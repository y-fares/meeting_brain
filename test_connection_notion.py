from dotenv import load_dotenv
import os

from database import create_session, Todo, Meeting
from integrations.notion_client import push_todo_to_notion



NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

session = create_session()
todo = session.query(Todo).first()
meeting = session.query(Meeting).filter_by(id=todo.meeting_id).first()

print(todo.id, todo.task)
page_id = push_todo_to_notion(todo, meeting)
print("Created page id:", page_id)
