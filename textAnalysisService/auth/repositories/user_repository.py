from sqlalchemy.orm import Session

from textAnalysisService.auth import models
from textAnalysisService.auth.schema import *
from sqlalchemy import or_


class UserRepository:
	def __init__(self, session: Session):
		self.session = session
	
	async def register_user(self, register_user_request: RegisteredUserCreate) -> models.RegisteredUser:
		"""create a user into the database"""
		new_user = models.RegisteredUser(user_name=register_user_request.user_name, email=register_user_request.email,
		                                 password=register_user_request.password)
		self.session.add(new_user)
		self.session.flush()  # Executes the INSERT statement
		return new_user
	
	async def verify_existing_user(self, email: str, user_name: str) -> Optional[models.RegisteredUser]:
		"""Retrieve a user by email or username from the database."""
		return self.session.query(models.RegisteredUser).filter(
			or_(models.RegisteredUser.email == email, models.RegisteredUser.user_name == user_name)
		).first()
