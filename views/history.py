from database import create_session, Meeting, Decision, Todo, Participant
import streamlit as st

def render_history_view():
    session = create_session()

    meetings = session.query(Meeting).order_by(Meeting.date.desc()).all()
    if not meetings:
        st.info("No meetings found yet.")
        return

    options = {f"Meeting #{m.id} - {m.date}": m.id for m in meetings}
    selected_label = st.selectbox("Select a meeting", list(options.keys()))
    meeting_id = options[selected_label]

    meeting = session.query(Meeting).filter_by(id=meeting_id).first()

    st.subheader("Summary")
    st.markdown(meeting.summary or "_No summary available_")

    st.subheader("Decisions")
    decisions = session.query(Decision).filter_by(meeting_id=meeting_id).all()
    if decisions:
        for d in decisions:
            st.markdown(f"- {d.text}")
    else:
        st.info("No decisions recorded.")

    st.subheader("Actions (TODOs)")
    todos = session.query(Todo).filter_by(meeting_id=meeting_id).all()
    if todos:
        data = [
            {
                "Task": t.task,
                "Owner": t.owner,
                "Due date": t.due_date,
                "Status": t.status,
            }
            for t in todos
        ]
        st.table(data)
    else:
        st.info("No TODOs registered.")

    st.subheader("Participants")
    participants = session.query(Participant).filter_by(meeting_id=meeting_id).all()
    if participants:
        for p in participants:
            st.markdown(f"- {p.name}")
    else:
        st.info("No participants detected.")

    with st.expander("Raw notes"):
        st.text(meeting.raw_text)
