from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, JSONParser
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse
import pandas as pd
import logging
from .models import UploadedFile
from .analysis.question_generator import generate_questions
from .analysis.query_processor import process_query
import os
from django.conf import settings  # Add this import at the top of the file

logger = logging.getLogger(__name__)

def index():
    return("Hello")

@api_view(['POST'])
@parser_classes([MultiPartParser])
def upload_excel(request):
    try:
        file_obj = request.FILES.get('file')
        
        if not file_obj:
            return Response(
                {'error': 'No file provided'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Check for both Excel and CSV file extensions
        if not file_obj.name.lower().endswith(('.xlsx', '.xls', '.csv')):
            return Response(
                {'error': 'Invalid file type. Please upload an Excel (.xlsx, .xls) or CSV (.csv) file'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Create the uploads directory if it doesn't exist
            os.makedirs(os.path.join(settings.MEDIA_ROOT, 'uploads'), exist_ok=True)
            
            # Create the model instance
            uploaded = UploadedFile(file=file_obj)
            uploaded.save()
            
            # Read the file based on its extension
            file_extension = file_obj.name.split('.')[-1].lower()
            if file_extension in ['xlsx', 'xls']:
                df = pd.read_excel(uploaded.file.path)
            else:  # CSV
                df = pd.read_csv(uploaded.file.path)
            
            # Replace inf/-inf with None and convert to native Python types
            df = df.replace([float('inf'), float('-inf')], None)
            
            # Generate questions based on the data
            questions = generate_questions(df)
            
            # Convert DataFrame to dict, handling non-serializable values
            preview_data = df.head().replace({float('nan'): None}).to_dict(orient='records')
            
            return Response({
                'success': True,
                'file_id': str(uploaded.id),
                'file_name': uploaded.original_name,
                'file_type': file_extension,
                'columns': [str(col) for col in df.columns],
                'questions': questions,
                'preview_data': preview_data,
                'row_count': len(df)
            })
            
        except Exception as e:
            # Clean up the file if it was created
            if 'uploaded' in locals() and hasattr(uploaded, 'id'):
                if hasattr(uploaded, 'file') and uploaded.file:
                    uploaded.file.delete(save=False)
                uploaded.delete()
            logger.error(f"Error processing file: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Error processing file: {str(e)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
    except Exception as e:
        logger.error(f"Upload error: {str(e)}", exc_info=True)
        return Response(
            {'error': 'Internal server error'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@parser_classes([JSONParser])
def run_query(request):
    """
    Process a query on the uploaded data
    """
    try:
        file_id = request.data.get('file_id')
        question = request.data.get('question')
        
        if not file_id or not question:
            return Response(
                {'error': 'Both file_id and question are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            file_record = UploadedFile.objects.get(id=file_id)
            file_path = file_record.file.path
            
            # Debug logging
            logger.info(f"Processing file with path: {file_path}")
            logger.info(f"File name: {file_record.file.name}")
            logger.info(f"File exists: {os.path.exists(file_path)}")
            
            # Get file extension from original name if available, otherwise from the path
            original_extension = os.path.splitext(file_record.original_name)[1].lower()
            path_extension = os.path.splitext(file_path)[1].lower()
            logger.info(f"Original extension: {original_extension}, Path extension: {path_extension}")
            
            # Try to determine the file type by content if extension is not reliable
            try:
                # First check the original extension if it exists
                if original_extension in ['.xlsx', '.xls', '.csv']:
                    engine = 'openpyxl' if original_extension == '.xlsx' else 'xlrd'
                # Then check the path extension
                elif path_extension in ['.xlsx', '.xls', '.csv']:
                    engine = 'openpyxl' if path_extension == '.xlsx' else 'xlrd'
                # If no extension, try to detect the file type
                else:
                    # Try with openpyxl first (for .xlsx)
                    try:
                        pd.read_excel(file_path, engine='openpyxl')
                        engine = 'openpyxl'
                    except Exception:
                        # Try with xlrd (for .xls)
                        try:
                            pd.read_excel(file_path, engine='xlrd')
                            engine = 'xlrd'
                        except Exception as e:
                            logger.error(f"Could not determine Excel file type: {str(e)}")
                            return Response(
                                {'error': 'Could not determine Excel file type. Please ensure the file is a valid .xlsx or .xls file'}, 
                                status=status.HTTP_400_BAD_REQUEST
                            )
            except Exception as e:
                logger.error(f"Error determining file type: {str(e)}")
                return Response(
                    {'error': 'Error processing the file. Please ensure it is a valid Excel file.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if original_extension == '.csv':
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path, engine=engine)
            
            # Handle potential parsing issues
            if df.empty:
                return Response(
                    {'error': 'The Excel file is empty or could not be read properly'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Process the query using your query processor
            result = process_query(df, question)
            
            return Response({
                'success': True,
                'file_id': file_id,
                'question': question,
                'result': result,
                'timestamp': file_record.uploaded_at.isoformat()
            })
            
        except UploadedFile.DoesNotExist:
            return Response(
                {'error': 'File not found or has been deleted'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except pd.errors.EmptyDataError:
            return Response(
                {'error': 'The Excel file is empty or contains no data'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except (ValueError, KeyError) as e:
            logger.error(f"Excel parsing error: {str(e)}")
            return Response(
                {'error': f'Error reading Excel file: {str(e)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except ImportError as e:
            logger.error(f"Required Excel library not found: {str(e)}")
            return Response(
                {'error': 'Server error: Required Excel processing library not installed'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            logger.error(f"Query processing error: {str(e)}", exc_info=True)
            error_msg = str(e)
            if 'No engine for filetype' in error_msg or 'Excel file format cannot be determined' in error_msg:
                error_msg = 'Unsupported Excel file format. Please ensure the file is a valid .xlsx or .xls file.'
            return Response(
                {'error': f'Error processing your query: {error_msg}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
    except Exception as e:
        logger.error(f"Run query error: {str(e)}")
        return Response(
            {'error': 'Internal server error'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
