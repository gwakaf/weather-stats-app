#!/usr/bin/env python3
"""
Graph Generator Utilities for Weather Finder
Generates historical weather graphs using matplotlib
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import io
import base64
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

def generate_historical_graphs(
    historical_data: List[Dict[str, Any]], 
    location: str, 
    unit: str = 'celsius'
) -> Dict[str, str]:
    """
    Generate historical weather graphs for 10 years of data
    
    Args:
        historical_data: List of weather data dictionaries for the same date/time over multiple years
        location: Location name
        unit: Temperature unit ('celsius' or 'fahrenheit')
    
    Returns:
        Dictionary with base64-encoded PNG images for each graph type
    """
    if not historical_data or len(historical_data) == 0:
        logger.error("No historical data provided for graph generation")
        return {}
    
    try:
        # Convert to DataFrame
        df = pd.DataFrame(historical_data)
        
        # Ensure date column is datetime
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # Extract year for labeling
        df['year'] = df['date'].dt.year
        
        logger.info(f"Generating graphs for {len(df)} data points from {df['year'].min()} to {df['year'].max()}")
        
        graphs = {}
        
        # Generate temperature graph
        graphs['temperature_graph'] = _generate_temperature_graph(df, location, unit)
        
        # Generate wind speed graph
        graphs['wind_graph'] = _generate_wind_graph(df, location, unit)
        
        # Generate precipitation graph
        graphs['precipitation_graph'] = _generate_precipitation_graph(df, location)
        
        # Generate cloud coverage graph
        graphs['cloud_coverage_graph'] = _generate_cloud_coverage_graph(df, location)
        
        # Calculate statistics
        graphs['stats'] = _calculate_statistics(df, unit)
        
        return graphs
        
    except Exception as e:
        logger.error(f"Error generating historical graphs: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {}


def _generate_temperature_graph(df: pd.DataFrame, location: str, unit: str) -> str:
    """Generate temperature history graph"""
    try:
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Convert to Fahrenheit if needed
        if unit == 'fahrenheit':
            temps = df['temperature_celsius'] * 9/5 + 32
            unit_label = '°F'
        else:
            temps = df['temperature_celsius']
            unit_label = '°C'
        
        # Plot line graph
        ax.plot(df['year'], temps, marker='o', linewidth=2, markersize=8, color='#FF6B6B')
        
        # Add trend line
        z = np.polyfit(df['year'], temps, 1)
        p = np.poly1d(z)
        ax.plot(df['year'], p(df['year']), "--", alpha=0.5, color='#333', label=f'Trend')
        
        # Formatting
        ax.set_xlabel('Year', fontsize=12, fontweight='bold')
        ax.set_ylabel(f'Temperature ({unit_label})', fontsize=12, fontweight='bold')
        ax.set_title(f'Temperature History - {location}\nLast 10 Years', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        # Set integer years on x-axis
        ax.set_xticks(df['year'])
        ax.set_xticklabels(df['year'], rotation=45)
        
        plt.tight_layout()
        
        # Convert to base64
        return _fig_to_base64(fig)
        
    except Exception as e:
        logger.error(f"Error generating temperature graph: {e}")
        return ""
    finally:
        plt.close('all')


def _generate_wind_graph(df: pd.DataFrame, location: str, unit: str) -> str:
    """Generate wind speed history graph"""
    try:
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Convert to mph if needed
        if unit == 'fahrenheit':
            wind = df['wind_speed_kmh'] * 0.621371
            unit_label = 'mph'
        else:
            wind = df['wind_speed_kmh']
            unit_label = 'km/h'
        
        # Plot bar graph
        ax.bar(df['year'], wind, color='#4ECDC4', alpha=0.7, edgecolor='#333', linewidth=1.5)
        
        # Formatting
        ax.set_xlabel('Year', fontsize=12, fontweight='bold')
        ax.set_ylabel(f'Wind Speed ({unit_label})', fontsize=12, fontweight='bold')
        ax.set_title(f'Wind Speed History - {location}\nLast 10 Years', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
        
        # Set integer years on x-axis
        ax.set_xticks(df['year'])
        ax.set_xticklabels(df['year'], rotation=45)
        
        plt.tight_layout()
        
        # Convert to base64
        return _fig_to_base64(fig)
        
    except Exception as e:
        logger.error(f"Error generating wind graph: {e}")
        return ""
    finally:
        plt.close('all')


def _generate_precipitation_graph(df: pd.DataFrame, location: str) -> str:
    """Generate precipitation history graph"""
    try:
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Plot bar graph
        ax.bar(df['year'], df['precipitation_mm'], color='#95E1D3', alpha=0.7, edgecolor='#333', linewidth=1.5)
        
        # Formatting
        ax.set_xlabel('Year', fontsize=12, fontweight='bold')
        ax.set_ylabel('Precipitation (mm)', fontsize=12, fontweight='bold')
        ax.set_title(f'Precipitation History - {location}\nLast 10 Years', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
        
        # Set integer years on x-axis
        ax.set_xticks(df['year'])
        ax.set_xticklabels(df['year'], rotation=45)
        
        plt.tight_layout()
        
        # Convert to base64
        return _fig_to_base64(fig)
        
    except Exception as e:
        logger.error(f"Error generating precipitation graph: {e}")
        return ""
    finally:
        plt.close('all')


def _generate_cloud_coverage_graph(df: pd.DataFrame, location: str) -> str:
    """Generate cloud coverage history graph"""
    try:
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Plot area graph
        ax.fill_between(df['year'], df['cloud_coverage_percent'], alpha=0.5, color='#A8DADC')
        ax.plot(df['year'], df['cloud_coverage_percent'], marker='o', linewidth=2, markersize=8, color='#457B9D')
        
        # Formatting
        ax.set_xlabel('Year', fontsize=12, fontweight='bold')
        ax.set_ylabel('Cloud Coverage (%)', fontsize=12, fontweight='bold')
        ax.set_title(f'Cloud Coverage History - {location}\nLast 10 Years', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 100)
        
        # Set integer years on x-axis
        ax.set_xticks(df['year'])
        ax.set_xticklabels(df['year'], rotation=45)
        
        plt.tight_layout()
        
        # Convert to base64
        return _fig_to_base64(fig)
        
    except Exception as e:
        logger.error(f"Error generating cloud coverage graph: {e}")
        return ""
    finally:
        plt.close('all')


def _calculate_statistics(df: pd.DataFrame, unit: str) -> Dict[str, Any]:
    """Calculate statistical information about the historical data"""
    try:
        temps = df['temperature_celsius'] if unit == 'celsius' else df['temperature_celsius'] * 9/5 + 32
        temp_unit = '°C' if unit == 'celsius' else '°F'
        
        wind_unit = 'km/h' if unit == 'celsius' else 'mph'
        wind = df['wind_speed_kmh'] if unit == 'celsius' else df['wind_speed_kmh'] * 0.621371
        
        return {
            'temperature': {
                'min': f"{temps.min():.1f}{temp_unit}",
                'max': f"{temps.max():.1f}{temp_unit}",
                'avg': f"{temps.mean():.1f}{temp_unit}",
                'range': f"{temps.min():.1f}{temp_unit} - {temps.max():.1f}{temp_unit}"
            },
            'wind': {
                'min': f"{wind.min():.1f} {wind_unit}",
                'max': f"{wind.max():.1f} {wind_unit}",
                'avg': f"{wind.mean():.1f} {wind_unit}",
                'range': f"{wind.min():.1f} - {wind.max():.1f} {wind_unit}"
            },
            'precipitation': {
                'min': f"{df['precipitation_mm'].min():.1f} mm",
                'max': f"{df['precipitation_mm'].max():.1f} mm",
                'avg': f"{df['precipitation_mm'].mean():.1f} mm",
                'total': f"{df['precipitation_mm'].sum():.1f} mm"
            },
            'cloud_coverage': {
                'min': f"{df['cloud_coverage_percent'].min():.0f}%",
                'max': f"{df['cloud_coverage_percent'].max():.0f}%",
                'avg': f"{df['cloud_coverage_percent'].mean():.0f}%"
            }
        }
    except Exception as e:
        logger.error(f"Error calculating statistics: {e}")
        return {}


def _fig_to_base64(fig) -> str:
    """Convert matplotlib figure to base64-encoded PNG"""
    try:
        buffer = io.BytesIO()
        fig.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        buffer.close()
        return image_base64
    except Exception as e:
        logger.error(f"Error converting figure to base64: {e}")
        return ""

