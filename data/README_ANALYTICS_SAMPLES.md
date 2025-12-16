# Sample Data Files for Testing Analytics View

This directory contains sample meeting text files that you can use to test the **Analytics & Exports** functionality.

## How to Use

1. **Import the meetings**:
   - Go to "Analyze Meeting" in the Streamlit app
   - Copy and paste the content of each sample file
   - Click "Analyze meeting" for each file
   - This will populate your database with meetings, decisions, and TODOs

2. **Test the Analytics view**:
   - Navigate to "Analytics" in the sidebar
   - Check the KPIs (Total Meetings, Total TODOs, % Completed, Overdue TODOs)
   - Review the summary tables
   - Download the CSV exports

## Sample Files Description

### `sample_analytics_1.txt` - Sprint Planning Q1
- **Date**: 2025-01-15
- **5 TODOs** with various owners (Karim, Sarah, Yacine, Lucie, Julien)
- **4 Decisions**
- **Status**: All TODOs will be "pending" by default

### `sample_analytics_2.txt` - Technical Architecture
- **Date**: 2025-01-20
- **4 TODOs** with technical focus
- **4 Decisions** about architecture choices
- **Owners**: Yacine, Julien, Paul, Mélanie

### `sample_analytics_3.txt` - Sprint Review 1
- **Date**: 2025-02-05
- **4 TODOs** (some marked as completed/in_progress in comments)
- **4 Decisions**
- **Note**: Status comments won't be automatically parsed - you'll need to manually update statuses in "All TODOs" view

### `sample_analytics_4.txt` - Client Presentation
- **Date**: 2025-02-10
- **4 TODOs** with client-related actions
- **4 Decisions** including beta testing plan
- **Owners**: Karim, Sarah, Yacine

### `sample_analytics_5.txt` - Sprint Retrospective
- **Date**: 2025-02-15
- **4 TODOs** focused on process improvements
- **4 Decisions** about team improvements
- **Owners**: Sarah, Yacine, Paul, Julien

### `sample_analytics_6.txt` - Production Incident
- **Date**: 2025-02-18
- **4 TODOs** (some marked as completed in comments)
- **4 Decisions** about incident response
- **Owners**: Paul, Yacine, Mélanie, Karim

### `sample_analytics_overdue.txt` - Overdue Tasks Review
- **Date**: 2025-02-20
- **6 TODOs** with **past due dates** (2025-02-10, 2025-02-12, 2025-02-15, 2025-02-18)
- **4 Decisions** about handling delays
- **Perfect for testing "Overdue TODOs" KPI**

## Expected Results After Import

After importing all 7 sample files, you should have:

- **7 Meetings** (different dates from Jan 15 to Feb 20, 2025)
- **~29 TODOs** (various owners, statuses, and due dates)
- **~28 Decisions** (4 per meeting on average)

## Testing Scenarios

### 1. Test KPIs
- **Total Meetings**: Should show 7
- **Total TODOs**: Should show ~29
- **% Completed**: Will be 0% initially (unless you manually mark some as completed)
- **Overdue TODOs**: Should show 4+ after importing `sample_analytics_overdue.txt`

### 2. Test Summary Tables
- **TODOs by Owner and Status**: Should show distribution across owners (Karim, Sarah, Yacine, Lucie, Julien, Paul, Mélanie)
- **TODOs by Meeting and Status**: Should show distribution per meeting
- **Decisions by Meeting**: Should show ~4 decisions per meeting

### 3. Test CSV Exports
- **Meetings CSV**: Should contain 7 rows with columns: id, date, title, summary
- **TODOs CSV**: Should contain ~29 rows with all TODO details including meeting info
- **Decisions CSV**: Should contain ~28 rows with decision text and meeting info

## Manual Status Updates

To test the "% Completed" KPI and status-based analytics:

1. Go to "All TODOs" view
2. Select TODOs and mark them as:
   - **Acknowledged** (status: in_progress)
   - **Done** (status: completed)
3. Return to "Analytics" to see updated KPIs

## Notes

- Due dates are in format `YYYY-MM-DD` (e.g., `2025-02-10`)
- Status comments in the files (like "STATUS: completed") are **not automatically parsed** - you need to manually update statuses in the UI
- The Analytics view calculates overdue TODOs by comparing `due_date` with today's date
- Only non-completed TODOs with past due dates are counted as overdue

## Power BI Integration

The CSV exports are designed to be Power BI-ready:
- UTF-8 encoding
- No index column
- Clean column names
- Proper date formatting
- All relationships preserved (meeting_id, etc.)

You can directly import these CSVs into Power BI for advanced analytics and visualizations.

