from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel

# Create the FastAPI application instance.
app = FastAPI()


# 1. Define a Pydantic model (the DTO).
class Message(BaseModel):
    message: str


# 2. Define the root endpoint.
@app.get("/")
def read_root():
    return {"Hello": "World"}


# Defines the file upload endpoint
@app.post("/uploadfile/")
async def create_upload_file(file: UploadFile):
    # Asynchronously read the file's contents.
    contents = await file.read()

    # Return the filename and the length of the contents.
    return {"filename": file.filename,
            "content_lenghth": len(contents),
            "content_type": file.content_type,
            "size": file.size
            }
