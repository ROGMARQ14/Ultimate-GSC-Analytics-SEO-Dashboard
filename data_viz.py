import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import List, Dict, Any
import numpy as np

class DataVisualizer:
    """Handle data visualization and analysis for GSC data"""
    
    @staticmethod
    def format_metrics(df: pd.DataFrame) -> pd.DataFrame:
        """Format metrics for display"""
        if df.empty:
            return df
            
        # Format CTR as percentage
        ctr_cols = [col for col in df.columns if 'ctr' in col.lower()]
        for col in ctr_cols:
            df[col] = df[col].round(1).astype(str) + '%'
            
        # Format position to 1 decimal place
        pos_cols = [col for col in df.columns if 'position' in col.lower()]
        for col in pos_cols:
            df[col] = df[col].round(1)
            
        return df

    @staticmethod
    def create_comparison_chart(
        df: pd.DataFrame,
        metric: str,
        periods: List[str]
    ) -> go.Figure:
        """Create comparison chart for a metric across periods"""
        fig = go.Figure()
        
        for period in periods:
            col_name = f"{metric}_{period}"
            if col_name in df.columns:
                fig.add_trace(
                    go.Bar(
                        name=period,
                        x=df.index,
                        y=df[col_name],
                        hovertemplate=f"{period}<br>{metric}: %{{y}}<extra></extra>"
                    )
                )
        
        fig.update_layout(
            title=f"{metric.title()} Comparison",
            barmode='group',
            xaxis_title="URLs",
            yaxis_title=metric.title(),
            height=500
        )
        
        return fig

    @staticmethod
    def create_metric_summary(df: pd.DataFrame, periods: List[str]) -> Dict[str, Any]:
        """Create summary statistics for metrics"""
        summary = {}
        metrics = ['clicks', 'impressions', 'position', 'ctr']
        
        for metric in metrics:
            metric_data = {}
            for period in periods:
                col_name = f"{metric}_{period}"
                if col_name in df.columns:
                    metric_data[period] = {
                        'total': df[col_name].sum() if metric in ['clicks', 'impressions'] else df[col_name].mean(),
                        'avg': df[col_name].mean(),
                        'min': df[col_name].min(),
                        'max': df[col_name].max()
                    }
            summary[metric] = metric_data
            
        return summary

    @staticmethod
    def display_metric_cards(summary: Dict[str, Any], metric: str):
        """Display metric summary cards"""
        st.subheader(f"{metric.title()} Summary")
        
        cols = st.columns(len(summary[metric]))
        for col, (period, data) in zip(cols, summary[metric].items()):
            with col:
                st.metric(
                    label=f"{period}",
                    value=f"{data['total']:,.1f}" if metric in ['clicks', 'impressions'] else f"{data['avg']:,.1f}",
                    delta=None  # Can add period-over-period change here
                )
                st.caption(f"Min: {data['min']:,.1f}")
                st.caption(f"Max: {data['max']:,.1f}")
                st.caption(f"Avg: {data['avg']:,.1f}")

    @staticmethod
    def create_trend_chart(
        df: pd.DataFrame,
        metric: str,
        periods: List[str],
        top_n: int = 10
    ) -> go.Figure:
        """Create trend chart for top N URLs"""
        # Get top N URLs by total metric value
        total_metric = sum(df[f"{metric}_{period}"] for period in periods)
        top_urls = total_metric.nlargest(top_n).index
        
        df_top = df.loc[top_urls]
        
        fig = px.line(
            df_top,
            x=periods,
            y=[f"{metric}_{period}" for period in periods],
            title=f"Top {top_n} URLs - {metric.title()} Trend",
            labels={
                "value": metric.title(),
                "variable": "Period"
            },
            height=500
        )
        
        fig.update_layout(
            showlegend=True,
            xaxis_title="Period",
            yaxis_title=metric.title()
        )
        
        return fig

    @staticmethod
    def create_heatmap(
        df: pd.DataFrame,
        metric: str,
        periods: List[str]
    ) -> go.Figure:
        """Create heatmap for metric changes"""
        # Calculate period-over-period changes
        changes = pd.DataFrame(index=df.index)
        
        for i in range(len(periods)-1):
            current = f"{metric}_{periods[i]}"
            previous = f"{metric}_{periods[i+1]}"
            change_col = f"Change {periods[i]} vs {periods[i+1]}"
            
            if metric == 'ctr':
                # Handle percentage changes for CTR
                changes[change_col] = (
                    df[current].str.rstrip('%').astype(float) -
                    df[previous].str.rstrip('%').astype(float)
                )
            else:
                # Regular percentage change for other metrics
                changes[change_col] = (
                    (df[current] - df[previous]) / df[previous] * 100
                ).round(1)
        
        fig = px.imshow(
            changes.T,
            title=f"{metric.title()} Changes (%)",
            labels=dict(x="URL", y="Period Comparison", color="% Change"),
            aspect="auto",
            height=400
        )
        
        fig.update_layout(
            xaxis_tickangle=-45,
            yaxis_tickangle=0
        )
        
        return fig

    @staticmethod
    def prepare_export_data(
        df: pd.DataFrame,
        summary: Dict[str, Any],
        periods: List[str]
    ) -> Dict[str, pd.DataFrame]:
        """Prepare data for export"""
        # Main data
        export_data = {
            'url_metrics': df.copy()
        }
        
        # Summary data
        summary_data = []
        for metric, period_data in summary.items():
            for period, stats in period_data.items():
                row = {
                    'metric': metric,
                    'period': period,
                    **stats
                }
                summary_data.append(row)
        
        export_data['summary'] = pd.DataFrame(summary_data)
        
        return export_data
