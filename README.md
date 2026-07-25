# Data-Driven Inventory Planning for a Retail Pharmacy

A business analytics capstone project focused on solving real-world inventory management
problems for **Rahul Medical Store**, a standalone retail pharmacy in Sambalpur, Odisha,
using primary sales and purchase data.

## Overview

Rahul Medical Store has been operating since 2008, handling stock worth ₹90 lakh–1 crore,
but relies entirely on manual Excel tracking and staff supervision. This creates three
recurring problems:

- Frequent **expiry and wastage** of medicines due to unstructured stock tracking
- **Manual, experience-based** restocking decisions with no forecasting
- **Non-prescription medicine sales** that raise accountability and compliance concerns

This project analyzes five months (April–August 2025) of the store's real purchase and
sales registers to diagnose these issues and propose a practical, data-driven inventory
model the owner can actually use — without needing any technical background.

## Objectives

1. Evaluate stock movement and expiry trends to reduce wastage
2. Analyze the impact of non-prescription medicine sales on store accountability
3. Propose a data-driven model to optimize stock management using simple, replicable tools

## Data

- **Source:** Primary data collected directly from the store — sales register, purchase
  register, and expiry reports (April–August 2025)
- **Fields:** Date, Product Name, Batch No., Expiry Date, Quantity, MRP, GST, Amount
- **Collection method:** Field visits, owner/staff interviews, and manual digitization of
  handwritten registers and GST software records into Excel
- **Cleaning:** Removed blanks/duplicates, standardized date formats, corrected product
  name inconsistencies, validated numeric fields

## Methodology

| Stage | Techniques Used |
|---|---|
| Descriptive Analysis | Monthly sales & purchase trends, product-level performance (Pivot Tables & Charts) |
| Diagnostic Analysis | ABC Classification, Expiry Risk Analysis, Stock Age & Movement Analysis |
| Prescriptive Analysis | Reorder-level recommendations, FEFO strategy, digitization roadmap |

**Tools used:** Microsoft Excel (Pivot Tables, SUMIFS, IF, Conditional Formatting,
FORECAST.LINEAR/TREND), Pareto Analysis, ABC Classification

## Key Findings

- **ABC Classification:** ~41% of products (Category A) drive the majority of purchase
  value and require close monitoring; ~28–40% (Category C) are low-value, slow-moving items
- **Expiry Risk:** ~23% of stock fell into the "At-Risk" (near-expiry) category, with
  high-value items like Volini Gel, Multivitamin Syrup, and Insulin 30/70 contributing the
  most potential loss
- **Stock Age:** Several fast-moving OTC items (Disprin, Calpol, Ibuprofen, Cetirizine)
  showed nearly 7 months of average stock age, indicating slow rotation and expiry risk
- **Sales Trend:** Sales peaked in May following a heavy April procurement cycle, with
  stable demand from June–August
- **Stockouts vs. Overstocking:** Several essential medicines (e.g., Amoxicillin, ORS
  Sachets, Dolo 650mg) experienced stockouts, while others (Combiflam, Avil 25mg) were
  overstocked — highlighting the need for demand-based reorder levels

## Recommendations

- Set reorder levels based on prior-month sales data (e.g., restock at 20% remaining stock)
- Closely monitor Category A medicines to avoid stockouts and over-purchasing
- Tag and actively clear "At-Risk" inventory via discounts, bundling, or supplier returns
- Adopt a **First-Expire-First-Out (FEFO)** approach for stock rotation
- Digitize tracking with a simple Excel/Google Sheets dashboard using conditional
  formatting for at-risk and low-stock alerts
- Maintain a separate, tagged record for non-prescription (OTC) sales to improve
  accountability and compliance

## Project Structure

```
├── proposal_report.pdf       # Initial project proposal, objectives, and methodology plan
├── midterm_report.pdf        # Preliminary data collection and early findings
├── final_report.pdf          # Full analysis, results, and recommendations
├── final_presentation.pptx   # Summary presentation of the project
└── README.md
```

## Future Scope

- Extend data collection to a full year to capture seasonal demand patterns
- Build an interactive dashboard (Power BI / Google Sheets) for real-time stock visibility
- Add sales forecasting models and automated expiry alerts
- Incorporate supplier performance analysis

## Author

**Spandan Bhoi**
B.Tech, Industrial Design
