"""
This is or model layer.
"""
# python
from typing import List, Optional

# 3rd
from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import (
    Session,
    declarative_base,
    relationship,
    sessionmaker,
)

# local
from src.utils import constants

Base = declarative_base()


class RequiredField(Exception):
    def __init__(self, field: str) -> None:
        self.field = field
        super().__init__(f'Please, the field {self.field} is required.')


class AlreadyRegistered(Exception):
    def __init__(self, field: str) -> None:
        self.field = field
        super().__init__(f'Sorry, {self.field} is already in use.')


class NotRegistered(Exception):
    pass


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    todos = relationship('Todo', back_populates='user')

    def __repr__(self) -> str:
        return f'<User username: {self.username}>'


class Todo(Base):
    __tablename__ = 'todo'

    id = Column(Integer, primary_key=True)
    description = Column(String, nullable=False)
    completed = Column(Boolean, nullable=False, default=False)
    id_user = Column(Integer, ForeignKey('user.id'))
    user = relationship('User', back_populates='todos')

    def __repr__(self) -> str:
        return f'<Todo description: {self.description},  completed: {self.completed}>'


class DataBase:
    def __init__(self, db_name: str) -> None:
        """This class will configure our database."""
        engine = create_engine(f'sqlite:///{db_name}')
        Base.metadata.create_all(engine)
        Session = sessionmaker(engine)
        self.session = Session()
        self.create_default_user()

    def create_default_user(self) -> None:
        username = constants.DEFAULT_USERNAME
        password = constants.DEFAULT_PASSWORD
        if not self.filter_users(username=username):
            user = User(username=username, password=password)
            self.insert_user(user)

    def insert_user(self, user: 'User') -> None:
        if user.username is None:
            raise RequiredField('username')

        elif user.password is None:
            raise RequiredField('password')

        elif self.filter_users(username=user.username):
            raise AlreadyRegistered('username')

        self.session.add(user)
        self.session.commit()

    def insert_todo(self, todo: 'Todo') -> None:
        if todo.description is None:
            raise RequiredField('description')

        self.session.add(todo)
        self.session.commit()

    def update_todo(self, todo: 'Todo') -> None:
        if todo.description is None:
            raise RequiredField('description')

        if todo.completed is None:
            raise RequiredField('completed')

        self.session.commit()

    def delete_user(self, user: 'User') -> None:
        self.session.delete(user)
        self.session.commit()

    def delete_todo(self, todo: 'Todo') -> None:
        self.session.delete(todo)
        self.session.commit()

    def select_users(self) -> List['User']:
        return self.session.query(User).all()

    def select_todos(self) -> List['Todo']:
        return self.session.query(Todo).all()

    def select_user_by_id(self, id: int) -> Optional['User']:
        return self.session.query(User).filter(User.id == id).first()

    def select_todo_by_id(self, id: int) -> Optional['Todo']:
        return self.session.query(Todo).filter(Todo.id == id).first()

    def filter_users(self, **values) -> List['User']:
        return self.session.query(User).filter_by(**values).all()

    def filter_todos(self, **values) -> List['Todo']:
        return self.session.query(Todo).filter_by(**values).all()

    def register_user(
        self, username: Optional[str], password: Optional[str]
    ) -> 'User':
        if username is None:
            raise RequiredField('username')

        if password is None:
            raise RequiredField('password')

        if self.filter_users(username=username):
            raise AlreadyRegistered('username')

        user = User(username=username, password=password)
        self.insert_user(user)

        return user

    def login_user(
        self, username: Optional[str], password: Optional[str]
    ) -> 'User':
        if username is None:
            raise RequiredField('username')

        if password is None:
            raise RequiredField('password')

        users = self.filter_users(username=username, password=password)
        if not users:
            raise NotRegistered('Invalid username or password')
        else:
            return users[0]

    def register_todo(
        self,
        description: Optional[str],
        completed: Optional[bool],
        id_user: Optional[int],
    ) -> 'Todo':
        if description is None:
            raise RequiredField('description')

        if completed is None:
            raise RequiredField('completed')

        if id_user is None:
            raise RequiredField('id_user')

        todo = Todo(
            description=description, completed=completed, id_user=id_user
        )
        self.insert_todo(todo)

        return todo
