"""
Meeting Brain - Sprint 1: Text Ingestion
A Streamlit app for ingesting and previewing raw meeting notes.
"""

import streamlit as st


def get_text_statistics(text: str) -> dict:
    """
    Calculate basic statistics about the input text.
    
    Args:
        text: The input text string
        
    Returns:
        A dictionary containing character count and line count
    """
    return {
        "characters": len(text),
        "lines": len(text.splitlines())
    }


def get_user_input() -> str:
    """
    Display the text area input widget and return the user's input.
    
    Returns:
        The text entered by the user in the text area
    """
    return st.text_area(
        label="Paste your meeting notes here",
        height=300,
        placeholder="Paste the content of your meeting here..."
    )


def display_preview(text: str) -> None:
    """
    Display the raw meeting notes in a preview section with statistics.
    
    Args:
        text: The text to display in the preview
    """
    st.subheader("Raw meeting notes")
    
    # Display the raw text
    st.text(text)
    
    # Calculate and display statistics
    stats = get_text_statistics(text)
    st.caption(f"Characters: {stats['characters']} | Lines: {stats['lines']}")


def main():
    """
    Main function that builds and runs the Streamlit UI.
    """
    # Set page title
    st.title("Meeting Brain - Sprint 1")
    
    # Display description at the top
    st.markdown("""
    **Step 1: Text Ingestion**
    
    This is the first step of Meeting Brain. Paste your raw meeting notes below 
    to begin the analysis process. The app will capture and preview your notes 
    for validation.
    """)
    
    # Get user input
    meeting_notes = get_user_input()
    
    # Add analyze button
    if st.button("Analyze meeting"):
        # Validate input
        if not meeting_notes or meeting_notes.strip() == "":
            st.warning("Please paste some meeting notes before analyzing.")
        else:
            # Show success message
            st.success("Meeting notes successfully captured.")
            
            # Display preview
            display_preview(meeting_notes)


if __name__ == "__main__":
    main()

