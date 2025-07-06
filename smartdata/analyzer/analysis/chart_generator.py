import os
import uuid
import matplotlib
# Use non-interactive backend that doesn't require a display
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from django.conf import settings

def generate_chart(df, chart_type, col, col2=None):
    """
    Generate a chart and save it to a file.
    Returns the URL path to the saved chart.
    """
    try:
        # Create figure and axis
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Generate the appropriate plot
        if chart_type == "hist":
            sns.histplot(df[col], kde=True, ax=ax)
            ax.set_title(f'Distribution of {col}')
        elif chart_type == "bar":
            sns.countplot(x=df[col], ax=ax)
            ax.set_title(f'Count of {col}')
            plt.xticks(rotation=45)
        elif chart_type == "scatter" and col2:
            sns.scatterplot(x=df[col], y=df[col2], ax=ax)
            ax.set_title(f'Scatter plot: {col} vs {col2}')
        else:
            raise ValueError(f"Unsupported chart type: {chart_type}")
        
        # Configure layout
        plt.tight_layout()
        
        # Ensure the media directory exists
        charts_dir = os.path.join(settings.MEDIA_ROOT, 'charts')
        os.makedirs(charts_dir, exist_ok=True)
        
        # Generate unique filename and save
        file_name = f"{uuid.uuid4().hex}.png"
        chart_path = os.path.join(charts_dir, file_name)
        
        # Save the figure
        plt.savefig(chart_path, dpi=100, bbox_inches='tight')
        
        # Clean up
        plt.close(fig)
        
        # Return the URL path (relative to MEDIA_URL)
        return os.path.join(settings.MEDIA_URL, 'charts', file_name)
        
    except Exception as e:
        # Log the error and re-raise
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error generating chart: {str(e)}")
        raise
