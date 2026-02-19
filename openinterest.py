import pandas as pd
import sys


def find_top_common_stocks(oi_file, gainers_file, top_n=5):
    """
    Find top N common stocks between OI Spurts and Gainers files

    Parameters:
    - oi_file: Path to OI Spurts CSV file
    - gainers_file: Path to Gainers CSV file
    - top_n: Number of top stocks to return (default 5)

    Returns:
    - DataFrame with top N stocks sorted by combined score
    """

    # Read both CSV files
    print("📂 Reading files...")
    oi_data = pd.read_csv(oi_file)
    gainers_data = pd.read_csv(gainers_file)

    print(f"✓ OI Spurts: {len(oi_data)} stocks")
    print(f"✓ Gainers: {len(gainers_data)} stocks")

    # Get column names for symbols
    oi_symbol_col = oi_data.columns[0]
    gainers_symbol_col = gainers_data.columns[0]

    # Standardize symbols
    oi_data["Symbol_Clean"] = oi_data[oi_symbol_col].astype(str).str.strip().str.upper()
    gainers_data["Symbol_Clean"] = (
        gainers_data[gainers_symbol_col].astype(str).str.strip().str.upper()
    )

    # Find common stocks
    common_symbols = set(oi_data["Symbol_Clean"]).intersection(
        set(gainers_data["Symbol_Clean"])
    )
    print(f"\n🔍 Found {len(common_symbols)} common stocks")

    if len(common_symbols) == 0:
        print("❌ No common stocks found!")
        return None, None

    # Filter for common stocks
    oi_filtered = oi_data[oi_data["Symbol_Clean"].isin(common_symbols)].copy()
    gainers_filtered = gainers_data[
        gainers_data["Symbol_Clean"].isin(common_symbols)
    ].copy()

    # Merge data
    merged = pd.merge(
        oi_filtered, gainers_filtered, on="Symbol_Clean", suffixes=("_OI", "_Gainers")
    )

    # Calculate combined score
    # Score = (OI Change % * 0.6) + (Price Change % * 0.4)
    # Higher weight to OI change as it indicates institutional interest
    merged["OI_Change_%"] = pd.to_numeric(merged["%chng in OI"], errors="coerce")
    merged["Price_Change_%"] = pd.to_numeric(merged["%chng"], errors="coerce")
    merged["Combined_Score"] = (merged["OI_Change_%"] * 0.6) + (
        merged["Price_Change_%"] * 0.4
    )

    # Sort by combined score
    merged_sorted = merged.sort_values("Combined_Score", ascending=False)

    # Get top N
    top_stocks = merged_sorted.head(top_n)

    # Create clean output
    result = pd.DataFrame(
        {
            "Rank": range(1, len(top_stocks) + 1),
            "Symbol": top_stocks["Symbol_Clean"].values,
            "Current_Price": top_stocks["Underlying value"].values,
            "Price_Change_%": top_stocks["Price_Change_%"].values,
            "OI_Change_%": top_stocks["OI_Change_%"].values,
            "OI_Change_Contracts": top_stocks["chng in OI"].values,
            "Volume": top_stocks["Volume_Gainers"].values,
            "Combined_Score": top_stocks["Combined_Score"].values,
        }
    )

    return result, merged_sorted


def print_detailed_report(result_df):
    """Print a detailed formatted report"""
    print("\n" + "=" * 100)
    print("🏆 TOP 5 TRADING OPPORTUNITIES - OI SPURTS + PRICE GAINERS")
    print("=" * 100)

    for idx, row in result_df.iterrows():
        rating = (
            "🔥 SUPER HOT"
            if row["Combined_Score"] > 20
            else "🔥 HOT" if row["Combined_Score"] > 10 else "✓ Good"
        )

        print(f"\n#{row['Rank']} {rating} - {row['Symbol']}")
        print(f"{'─'*80}")
        print(f"   💰 Price: ₹{row['Current_Price']:.2f}")
        print(f"   📈 Price Change: {row['Price_Change_%']:.2f}%")
        print(
            f"   📊 OI Change: {row['OI_Change_%']:.2f}% ({int(row['OI_Change_Contracts']):,} contracts)"
        )
        print(f"   📦 Volume: {int(row['Volume']):,} shares")
        print(f"   ⭐ Combined Score: {row['Combined_Score']:.2f}")


def main():
    # File paths
    oi_file = r"C:\Users\PC\Downloads\Spurts-in-OI-By-Underlying-14012026.csv"
    gainers_file = r"C:\Users\PC\Downloads\T20-GL-gainers-FOSec-14-Jan-2026.csv"

    print("🚀 Stock Analysis - Finding Top 5 Opportunities")
    print("=" * 100)

    # Find top 5 common stocks
    result, full_data = find_top_common_stocks(oi_file, gainers_file, top_n=5)

    if result is not None:
        # Print detailed report
        print_detailed_report(result)

        # Save results
        output_file = "/mnt/user-data/outputs/top_5_trading_opportunities.csv"
        result.to_csv(output_file, index=False)

        # Save full common stocks data
        full_output = "/mnt/user-data/outputs/all_common_stocks_ranked.csv"

        full_clean = pd.DataFrame(
            {
                "Symbol": full_data["Symbol_Clean"].values,
                "Current_Price": full_data["Underlying value"].values,
                "Price_Change_%": full_data["Price_Change_%"].values,
                "OI_Change_%": full_data["OI_Change_%"].values,
                "OI_Change_Contracts": full_data["chng in OI"].values,
                "Volume": full_data["Volume_Gainers"].values,
                "Combined_Score": full_data["Combined_Score"].values,
            }
        )

        full_clean.to_csv(full_output, index=False)

        print("\n" + "=" * 100)
        print("✅ SUCCESS! Files saved:")
        print(f"   1. {output_file}")
        print(f"   2. {full_output}")
        print("=" * 100)

        # Print summary table
        print("\n📊 SUMMARY TABLE:")
        print(result.to_string(index=False))

        return result
    else:
        print("❌ Analysis failed - no common stocks found")
        return None


if __name__ == "__main__":
    result = main()
