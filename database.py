from sqlmodel import SQLModel, create_engine

engine = create_engine("sqlite:///shortener.db")

def init_db():
    SQLModel.metadata.create_all(engine)
