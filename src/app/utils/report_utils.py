import sqlparse
import urllib.parse

def split_report_contents(report_contents: str) -> tuple[str, str, str]:
    """Split the report contents into subject, summary and expanded sections."""
    summary_marker = "## Summary"
    section_marker = "## "
    subject_marker = "### Subject"

    # Find the start of "### Subject"
    subject_start = report_contents.find(subject_marker)
    if subject_start == -1:
        # "### Subject" not found
        return None, report_contents, None
    
    # Find the end of Subject section (e.g. to exclude redundant extra line)
    subject_end = report_contents.find("**Review Summary Report", subject_start + len(subject_marker))

    # Find the start of "## Summary" (assumed to be after "### Subject")
    summary_start = report_contents.find(summary_marker)
    if subject_end == -1:
        subject_end = summary_start
    if summary_start == -1:
        # "## Summary" not found
        return report_contents[:subject_end], report_contents[subject_end:], None
    else:
        # Find the start of the next section after "## Summary"
        expanded_section_start = report_contents.find(section_marker, summary_start + len(summary_marker))
        
        if expanded_section_start == -1:
            # No more sections after "## Summary"
            return report_contents[:subject_end], report_contents[summary_start:], None
        else:
            return report_contents[:subject_end], report_contents[summary_start:expanded_section_start], report_contents[expanded_section_start:]


def format_sql_query(sql_query):
    """Format SQL query using sqlparse library"""
    formatted_sql = sqlparse.format(
        sql_query,
        keyword_case='upper',  # Makes keywords uppercase
        identifier_case=None,  # Preserves identifier case
        reindent=True,         # Adds proper indentation
        indent_width=2,        # Indentation width
        strip_comments=False,  # Preserves comments
        comma_first=False      # Commas at the end of line, not beginning
    )
    return formatted_sql

def str_to_url_encoding(string: str) -> str:
    """Convert a string to the format used in a Dashboard IFrame embedding."""
    once_encoded = urllib.parse.quote(string)
    twice_encoded = urllib.parse.quote(once_encoded)
    return twice_encoded