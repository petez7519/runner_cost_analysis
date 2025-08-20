#!/usr/bin/env python3
"""
Analyze costs specifically for runner executors in CircleCI usage data
Focus on network costs and other cost breakdowns for runners only

Usage:
    # Set the CSV file path via environment variable
    export CIRCLECI_USAGE_CSV="/path/to/your/usage.csv"
    python3 analyze_runner_costs.py
    
    # Or run with inline environment variable
    CIRCLECI_USAGE_CSV="/path/to/your/usage.csv" python3 analyze_runner_costs.py
    
    # If no environment variable is set, uses default path
    python3 analyze_runner_costs.py
"""

import pandas as pd
import sys
import os
from pathlib import Path
import numpy as np

def analyze_runner_executor_costs(csv_file):
    """Analyze all costs associated with runner executors"""
    
    print(f"Loading data from {csv_file}...")
    
    try:
        # Read CSV with error handling for inconsistent fields
        df = pd.read_csv(csv_file, on_bad_lines='skip', engine='python')
        print(f"✓ Loaded {len(df):,} total rows")
        
        # Filter for runner executor only
        print("\n" + "="*80)
        print("FILTERING FOR RUNNER EXECUTOR ONLY")
        print("="*80)
        
        runner_df = df[df['EXECUTOR'] == 'runner'].copy()
        print(f"✓ Found {len(runner_df):,} runner executor records out of {len(df):,} total records")
        print(f"✓ Runner executors represent {len(runner_df)/len(df)*100:.1f}% of all records")
        
        # Convert numeric columns with error handling
        credit_columns = ['COMPUTE_CREDITS', 'DLC_CREDITS', 'USER_CREDITS', 
                         'STORAGE_CREDITS', 'NETWORK_CREDITS', 'LEASE_CREDITS', 
                         'LEASE_OVERAGE_CREDITS', 'IPRANGES_CREDITS', 'TOTAL_CREDITS']
        
        for col in credit_columns:
            if col in runner_df.columns:
                runner_df[col] = pd.to_numeric(runner_df[col], errors='coerce').fillna(0)
        
        # Convert JOB_RUN_SECONDS to numeric, handling the problematic values
        if 'JOB_RUN_SECONDS' in runner_df.columns:
            runner_df['JOB_RUN_SECONDS'] = pd.to_numeric(runner_df['JOB_RUN_SECONDS'], errors='coerce')
        
        # Overall cost summary for runners
        print("\n" + "="*80)
        print("RUNNER EXECUTOR COST SUMMARY")
        print("="*80)
        
        total_runner_credits = runner_df['TOTAL_CREDITS'].sum()
        print(f"\nTotal Credits Used by Runners: {total_runner_credits:,.0f}")
        
        print("\nCost Breakdown by Category:")
        cost_breakdown = {}
        for col in credit_columns[:-1]:  # Exclude TOTAL_CREDITS
            if col in runner_df.columns:
                credit_sum = runner_df[col].sum()
                if credit_sum > 0:
                    cost_breakdown[col] = credit_sum
                    percentage = (credit_sum / total_runner_credits * 100) if total_runner_credits > 0 else 0
                    print(f"  • {col.replace('_CREDITS', ''):<20}: {credit_sum:>15,.0f} credits ({percentage:>5.1f}%)")
        
        # Network costs analysis for runners
        print("\n" + "="*80)
        print("NETWORK COSTS FOR RUNNER EXECUTORS")
        print("="*80)
        
        network_credits = runner_df['NETWORK_CREDITS'].sum()
        network_records = (runner_df['NETWORK_CREDITS'] > 0).sum()
        
        print(f"\nNetwork Cost Statistics:")
        print(f"  • Total Network Credits: {network_credits:,.0f}")
        print(f"  • Records with Network Costs: {network_records:,} out of {len(runner_df):,} ({network_records/len(runner_df)*100:.1f}%)")
        
        if network_records > 0:
            network_df = runner_df[runner_df['NETWORK_CREDITS'] > 0]
            print(f"  • Average Network Credits per Job (when present): {network_df['NETWORK_CREDITS'].mean():,.2f}")
            print(f"  • Median Network Credits per Job (when present): {network_df['NETWORK_CREDITS'].median():,.2f}")
            print(f"  • Max Network Credits for Single Job: {network_df['NETWORK_CREDITS'].max():,.0f}")
            print(f"  • Total Jobs with Network Costs: {network_records:,}")
        
        # Analyze by organization
        print("\n" + "="*80)
        print("RUNNER COSTS BY ORGANIZATION")
        print("="*80)
        
        org_summary = runner_df.groupby('ORGANIZATION_NAME').agg({
            'JOB_ID': 'count',
            'TOTAL_CREDITS': 'sum',
            'NETWORK_CREDITS': 'sum',
            'COMPUTE_CREDITS': 'sum',
            'STORAGE_CREDITS': 'sum',
            'IPRANGES_CREDITS': 'sum'
        }).round(0)
        
        org_summary.columns = ['Job_Count', 'Total_Credits', 'Network_Credits', 
                               'Compute_Credits', 'Storage_Credits', 'IPRanges_Credits']
        org_summary = org_summary.sort_values('Total_Credits', ascending=False)
        
        print("\nOrganization Summary:")
        for org in org_summary.index:
            total_creds = org_summary.loc[org, 'Total_Credits']
            if total_creds > 0:
                print(f"\n{org}:")
                print(f"  • Jobs: {org_summary.loc[org, 'Job_Count']:,.0f}")
                print(f"  • Total Credits: {total_creds:,.0f}")
                print(f"  • Network Credits: {org_summary.loc[org, 'Network_Credits']:,.0f} ({org_summary.loc[org, 'Network_Credits']/total_creds*100:.1f}%)")
                print(f"  • Compute Credits: {org_summary.loc[org, 'Compute_Credits']:,.0f} ({org_summary.loc[org, 'Compute_Credits']/total_creds*100:.1f}%)")
                print(f"  • IPRanges Credits: {org_summary.loc[org, 'IPRanges_Credits']:,.0f} ({org_summary.loc[org, 'IPRanges_Credits']/total_creds*100:.1f}%)")
        
        # Analyze by resource class - FIXED VERSION
        print("\n" + "="*80)
        print("RUNNER COSTS BY RESOURCE CLASS")
        print("="*80)
        
        # Create aggregation dict without the problematic mean calculation
        agg_dict = {
            'JOB_ID': 'count',
            'TOTAL_CREDITS': 'sum',
            'NETWORK_CREDITS': 'sum',
            'COMPUTE_CREDITS': 'sum'
        }
        
        # Only add JOB_RUN_SECONDS aggregation if we have valid numeric data
        if 'JOB_RUN_SECONDS' in runner_df.columns:
            valid_runtime = runner_df['JOB_RUN_SECONDS'].notna().sum()
            if valid_runtime > 0:
                # Calculate mean manually for each resource class
                resource_summary = runner_df.groupby('RESOURCE_CLASS').agg(agg_dict).round(0)
                
                # Add average runtime manually
                avg_runtimes = []
                for resource in resource_summary.index:
                    resource_data = runner_df[runner_df['RESOURCE_CLASS'] == resource]['JOB_RUN_SECONDS']
                    valid_data = resource_data.dropna()
                    if len(valid_data) > 0:
                        avg_runtimes.append(valid_data.mean())
                    else:
                        avg_runtimes.append(0)
                
                resource_summary['Avg_Runtime_Seconds'] = avg_runtimes
            else:
                resource_summary = runner_df.groupby('RESOURCE_CLASS').agg(agg_dict).round(0)
                resource_summary['Avg_Runtime_Seconds'] = 0
        else:
            resource_summary = runner_df.groupby('RESOURCE_CLASS').agg(agg_dict).round(0)
            resource_summary['Avg_Runtime_Seconds'] = 0
        
        resource_summary.columns = ['Job_Count', 'Total_Credits', 'Network_Credits', 
                                   'Compute_Credits', 'Avg_Runtime_Seconds']
        resource_summary = resource_summary.sort_values('Total_Credits', ascending=False)
        
        print("\nTop 15 Resource Classes by Total Cost:")
        for i, resource in enumerate(resource_summary.head(15).index, 1):
            job_count = resource_summary.loc[resource, 'Job_Count']
            total_creds = resource_summary.loc[resource, 'Total_Credits']
            
            print(f"\n{i}. {resource}:")
            print(f"   • Jobs: {job_count:,.0f}")
            print(f"   • Total Credits: {total_creds:,.0f}")
            print(f"   • Network Credits: {resource_summary.loc[resource, 'Network_Credits']:,.0f}")
            print(f"   • Compute Credits: {resource_summary.loc[resource, 'Compute_Credits']:,.0f}")
            
            if resource_summary.loc[resource, 'Avg_Runtime_Seconds'] > 0:
                print(f"   • Avg Runtime: {resource_summary.loc[resource, 'Avg_Runtime_Seconds']:,.0f} seconds")
            
            # Calculate cost per job
            if job_count > 0:
                cost_per_job = total_creds / job_count
                network_per_job = resource_summary.loc[resource, 'Network_Credits'] / job_count
                print(f"   • Avg Total Cost/Job: {cost_per_job:,.2f} credits")
                print(f"   • Avg Network Cost/Job: {network_per_job:,.2f} credits")
        
        # Top jobs by network costs
        print("\n" + "="*80)
        print("TOP RUNNER JOBS BY NETWORK COSTS")
        print("="*80)
        
        top_network_jobs = runner_df.nlargest(20, 'NETWORK_CREDITS')[
            ['JOB_NAME', 'ORGANIZATION_NAME', 'RESOURCE_CLASS', 'NETWORK_CREDITS', 
             'TOTAL_CREDITS', 'JOB_RUN_SECONDS']
        ]
        
        print("\nTop 20 Jobs with Highest Network Costs:")
        for idx, row in top_network_jobs.iterrows():
            network_pct = (row['NETWORK_CREDITS'] / row['TOTAL_CREDITS'] * 100) if row['TOTAL_CREDITS'] > 0 else 0
            print(f"\n• Job: {row['JOB_NAME']}")
            print(f"  Org: {row['ORGANIZATION_NAME']}")
            print(f"  Resource Class: {row['RESOURCE_CLASS']}")
            print(f"  Network Credits: {row['NETWORK_CREDITS']:,.0f} ({network_pct:.1f}% of total)")
            print(f"  Total Credits: {row['TOTAL_CREDITS']:,.0f}")
            if pd.notna(row['JOB_RUN_SECONDS']):
                print(f"  Runtime: {row['JOB_RUN_SECONDS']:,.0f} seconds")
        
        # Analyze utilization for runners
        print("\n" + "="*80)
        print("RUNNER RESOURCE UTILIZATION")
        print("="*80)
        
        # Convert utilization columns to numeric
        util_cols = ['MEDIAN_CPU_UTILIZATION_PCT', 'MAX_CPU_UTILIZATION_PCT', 
                    'MEDIAN_RAM_UTILIZATION_PCT', 'MAX_RAM_UTILIZATION_PCT']
        for col in util_cols:
            if col in runner_df.columns:
                runner_df[col] = pd.to_numeric(runner_df[col], errors='coerce')
        
        print("\nOverall Utilization Statistics:")
        for col in util_cols:
            if col in runner_df.columns:
                valid_data = runner_df[col].dropna()
                if len(valid_data) > 0:
                    print(f"\n{col.replace('_', ' ').title()}:")
                    print(f"  • Mean: {valid_data.mean():.1f}%")
                    print(f"  • Median: {valid_data.median():.1f}%")
                    print(f"  • 25th Percentile: {valid_data.quantile(0.25):.1f}%")
                    print(f"  • 75th Percentile: {valid_data.quantile(0.75):.1f}%")
        
        # Find underutilized runners with high network costs
        print("\n" + "="*80)
        print("UNDERUTILIZED RUNNERS WITH HIGH NETWORK COSTS")
        print("="*80)
        
        # Calculate 75th percentile of network credits for comparison
        network_75th = runner_df['NETWORK_CREDITS'].quantile(0.75)
        
        # Filter for low utilization but high network costs
        underutilized = runner_df[
            (runner_df['MAX_CPU_UTILIZATION_PCT'] < 50) & 
            (runner_df['MAX_RAM_UTILIZATION_PCT'] < 50) &
            (runner_df['NETWORK_CREDITS'] > network_75th)
        ]
        
        if len(underutilized) > 0:
            print(f"\nFound {len(underutilized)} runner jobs with <50% CPU/RAM utilization but high network costs:")
            print(f"(Network costs above 75th percentile: {network_75th:,.0f} credits)")
            
            underutil_summary = underutilized.groupby('RESOURCE_CLASS').agg({
                'JOB_ID': 'count',
                'NETWORK_CREDITS': 'sum',
                'TOTAL_CREDITS': 'sum',
                'MAX_CPU_UTILIZATION_PCT': 'mean',
                'MAX_RAM_UTILIZATION_PCT': 'mean'
            }).round(1)
            
            underutil_summary = underutil_summary.sort_values('NETWORK_CREDITS', ascending=False)
            
            print("\nResource classes with underutilized runners and high network costs:")
            for resource in underutil_summary.head(10).index:
                print(f"\n• {resource}:")
                print(f"  Jobs: {underutil_summary.loc[resource, 'JOB_ID']:.0f}")
                print(f"  Network Credits Wasted: {underutil_summary.loc[resource, 'NETWORK_CREDITS']:,.0f}")
                print(f"  Avg CPU Utilization: {underutil_summary.loc[resource, 'MAX_CPU_UTILIZATION_PCT']:.1f}%")
                print(f"  Avg RAM Utilization: {underutil_summary.loc[resource, 'MAX_RAM_UTILIZATION_PCT']:.1f}%")
        else:
            print("\nNo underutilized runners with high network costs found.")
        
        # Time-based analysis
        print("\n" + "="*80)
        print("RUNNER COSTS OVER TIME")
        print("="*80)
        
        # Convert date columns
        runner_df['JOB_RUN_DATE'] = pd.to_datetime(runner_df['JOB_RUN_DATE'], errors='coerce')
        
        # Filter for valid dates only
        valid_dates_df = runner_df[runner_df['JOB_RUN_DATE'].notna()].copy()
        
        if len(valid_dates_df) > 0:
            # Group by month
            valid_dates_df['Month'] = valid_dates_df['JOB_RUN_DATE'].dt.to_period('M')
            
            monthly_summary = valid_dates_df.groupby('Month').agg({
                'JOB_ID': 'count',
                'TOTAL_CREDITS': 'sum',
                'NETWORK_CREDITS': 'sum',
                'COMPUTE_CREDITS': 'sum'
            }).round(0)
            
            print("\nMonthly Runner Costs (Last 6 months with data):")
            for month in monthly_summary.tail(6).index:
                if pd.notna(month):
                    total_monthly = monthly_summary.loc[month, 'TOTAL_CREDITS']
                    if total_monthly > 0:
                        network_pct = (monthly_summary.loc[month, 'NETWORK_CREDITS'] / total_monthly * 100)
                        print(f"\n{month}:")
                        print(f"  • Jobs: {monthly_summary.loc[month, 'JOB_ID']:,.0f}")
                        print(f"  • Total Credits: {total_monthly:,.0f}")
                        print(f"  • Network Credits: {monthly_summary.loc[month, 'NETWORK_CREDITS']:,.0f} ({network_pct:.1f}%)")
        
        # Recommendations
        print("\n" + "="*80)
        print("RECOMMENDATIONS FOR RUNNER EXECUTOR OPTIMIZATION")
        print("="*80)
        
        network_pct_total = (network_credits/total_runner_credits*100) if total_runner_credits > 0 else 0
        
        print(f"""
Based on the runner executor analysis:

1. **Network Cost Optimization:**
   • Network costs represent {network_pct_total:.1f}% of total runner costs
   • {network_records:,} out of {len(runner_df):,} runner jobs incur network costs
   • Focus on jobs with high network credits but low resource utilization
   • Consider caching strategies for frequently downloaded dependencies
   
2. **Resource Class Optimization:**
   • Review resource classes with <50% CPU/RAM utilization
   • Downsize overprovisioned runners to reduce compute costs
   • Balance between compute and network costs
   
3. **Organization-Specific Actions:**""")
        
        for org in org_summary.index:
            org_total = org_summary.loc[org, 'Total_Credits']
            if org_total > 0:
                network_pct = org_summary.loc[org, 'Network_Credits']/org_total*100
                if network_pct > 5:
                    print(f"   • {org}: High network costs ({network_pct:.1f}% of total) - review data transfer patterns")
        
        print("""
4. **High-Impact Optimizations:**
   • Focus on top 20 jobs by network costs for immediate impact
   • Implement workspace persistence instead of artifacts where possible
   • Use shallow git clones to reduce repository transfer sizes
   • Consider regional runners to reduce cross-region data transfer
   • Review container image sizes and optimize Docker layer caching
        """)
        
    except Exception as e:
        print(f"Error analyzing file: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Get CSV file path from environment variable or use default
    csv_path = os.environ.get('CIRCLECI_USAGE_CSV')
    
    if csv_path:
        print(f"Using CSV file from environment variable: {csv_path}")
        csv_file = Path(csv_path)
    else:
        # Default path if no environment variable is set
        default_path = "/Users/Pete/Downloads/combined-usage-data-july-2025.csv"
        print(f"No CIRCLECI_USAGE_CSV environment variable found.")
        print(f"Using default path: {default_path}")
        print("\nTo use a different file, set the environment variable:")
        print("  export CIRCLECI_USAGE_CSV='/path/to/your/usage.csv'")
        print("  python3 analyze_runner_costs.py\n")
        csv_file = Path(default_path)
    
    if not csv_file.exists():
        print(f"Error: File not found: {csv_file}")
        print("\nPlease check that the file exists and the path is correct.")
        if not csv_path:
            print("\nYou can specify a different file by setting the CIRCLECI_USAGE_CSV environment variable:")
            print("  export CIRCLECI_USAGE_CSV='/path/to/your/usage.csv'")
            print("  python3 analyze_runner_costs.py")
        sys.exit(1)
    
    analyze_runner_executor_costs(csv_file)
