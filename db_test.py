from memory import NoteMemory

memory = NoteMemory(persist_path="./note_db")

coll = memory.store.get()
for idx, (doc_id, text) in enumerate(zip(coll["ids"], coll["documents"])):
    print(f"{idx+1}. ID: {doc_id}")
    print("Text:", text)
    print("Metadata:", coll["metadatas"][idx])
    print("—" * 40)

# memory.store.delete(ids=coll["ids"])