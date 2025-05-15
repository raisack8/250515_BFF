from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="Backend API")

# Sample data models
class Item(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

# In-memory database for demo
items_db = [
    Item(id=1, name="Item 1", description="This is item 1"),
    Item(id=2, name="Item 2", description="This is item 2"),
]

@app.get("/")
def read_root():
    return {"message": "Backend API is running"}

@app.get("/items", response_model=List[Item])
def read_items():
    return items_db

@app.get("/items/{item_id}", response_model=Item)
def read_item(item_id: int):
    for item in items_db:
        if item.id == item_id:
            return item
    raise HTTPException(status_code=404, detail="Item not found")

@app.post("/items", response_model=Item)
def create_item(item: Item):
    items_db.append(item)
    return item

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 