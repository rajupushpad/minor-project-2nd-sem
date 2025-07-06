import re
import logging
import pandas as pd
from .chart_generator import generate_chart

logger = logging.getLogger(__name__)

def process_query(df, question):
    """
    Process a natural language query and generate a response with optional visualization.
    
    Args:
        df (pd.DataFrame): The input data
        question (str): The natural language question
        
    Returns:
        dict: Contains 'summary' text and 'chart_url' if applicable
    """
    if not isinstance(df, pd.DataFrame) or df.empty:
        return {"summary": "Error: No data available for analysis", "chart_url": ""}
        
    if not question or not isinstance(question, str):
        return {"summary": "Error: Invalid question format", "chart_url": ""}
    
    try:
        question = question.strip()
        summary = ""
        chart_url = ""
        
        # Clean column names in the dataframe (remove extra spaces, etc.)
        df.columns = [str(col).strip() for col in df.columns]
        
        # Convert all string columns to string type to avoid comparison issues
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].astype(str).str.strip()
        
        # Handle different types of questions
        # Mean calculation
        if "mean of" in question.lower():
            match = re.search(r'mean of (\w+)', question, re.IGNORECASE)
            if not match:
                return {"summary": "Could not determine the column for mean calculation", "chart_url": ""}
            
            col = match.group(1).strip()
            if col not in df.columns:
                return {"summary": f"Column '{col}' not found in the data", "chart_url": ""}
                
            try:
                mean_value = pd.to_numeric(df[col], errors='coerce').mean()
                summary = f"The mean of {col} is {mean_value:.2f}"
            except Exception as e:
                logger.error(f"Error calculating mean: {str(e)}")
                return {"summary": f"Error calculating mean for column '{col}'. It may not contain numeric data.", "chart_url": ""}

        # Distribution
        elif "show distribution of" in question.lower():
            col = question.lower().replace("show distribution of", "").strip()
            if not col or col not in df.columns:
                return {"summary": f"Could not determine or find column '{col}' for distribution", "chart_url": ""}
                
            try:
                chart_url = generate_chart(df, chart_type="hist", col=col)
                summary = f"Distribution chart for {col}"
            except Exception as e:
                logger.error(f"Error generating distribution chart: {str(e)}")
                return {"summary": f"Error generating distribution chart: {str(e)}", "chart_url": ""}

        # Category count
        elif "show count of each category in" in question.lower():
            col = question.lower().replace("show count of each category in", "").strip()
            if not col or col not in df.columns:
                return {"summary": f"Could not determine or find column '{col}' for category count", "chart_url": ""}
                
            try:
                chart_url = generate_chart(df, chart_type="bar", col=col)
                summary = f"Category count chart for {col}"
            except Exception as e:
                logger.error(f"Error generating category count chart: {str(e)}")
                return {"summary": f"Error generating category count chart: {str(e)}", "chart_url": ""}

        # Correlation
        elif "find correlation between" in question.lower():
            parts = question.lower().replace("find correlation between", "").split("and")
            if len(parts) != 2:
                return {"summary": "Please specify exactly two columns for correlation", "chart_url": ""}
                
            col1, col2 = [part.strip() for part in parts]
            
            if col1 not in df.columns or col2 not in df.columns:
                return {
                    "summary": f"Could not find one or both columns: '{col1}' and '{col2}'", 
                    "chart_url": ""
                }
                
            try:
                # Convert to numeric, coerce errors to NaN
                series1 = pd.to_numeric(df[col1], errors='coerce')
                series2 = pd.to_numeric(df[col2], errors='coerce')
                
                # Drop NA values for correlation calculation
                valid_data = pd.concat([series1, series2], axis=1).dropna()
                
                if len(valid_data) < 2:
                    return {
                        "summary": f"Not enough valid numeric data to calculate correlation between {col1} and {col2}", 
                        "chart_url": ""
                    }
                    
                corr = valid_data[col1].corr(valid_data[col2])
                chart_url = generate_chart(df, chart_type="scatter", col=col1, col2=col2)
                summary = f"Correlation between {col1} and {col2} is {corr:.2f}"
            except Exception as e:
                logger.error(f"Error calculating correlation: {str(e)}")
                return {"summary": f"Error calculating correlation: {str(e)}", "chart_url": ""}

        # Default response if no pattern matches
        else:
            return {
                "summary": "I couldn't process that question. Here's what I can help with:\n"
                          "- 'What is the mean of [column]?'\n"
                          "- 'Show distribution of [column]'\n"
                          "- 'Show count of each category in [column]'\n"
                          "- 'Find correlation between [column1] and [column2]'",
                "chart_url": ""
            }

        return {
            "summary": summary,
            "chart_url": chart_url
        }
        
    except Exception as e:
        logger.error(f"Unexpected error in process_query: {str(e)}")
        return {
            "summary": "An unexpected error occurred while processing your query. Please try again.",
            "chart_url": ""
        }
