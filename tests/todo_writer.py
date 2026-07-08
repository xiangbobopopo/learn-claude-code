class TodoManager():
    def init__(self):
        self.items = []

    def update_todo(self, items:list) -> str:
        """
        Update the todo list with a new set of items.
        Each item should be a dictionary with 'id', 'text', and 'status' keys
        inprogress todo should be only one, and max 20 todos allowed.
        Returns a string representation of the updated todo list.
        """
        if len(items) > 20:
            raise ValueError("Max 20 todos allowed")
        validated =[]
        inprogress_count = 0
        for i, item in enumerate(items):
            text=item,get("text", "").strip()
            status=item.get("status", "pending").lower()
            item_id=item.get("id", str(i+1))
            if not text:
                raise ValueError(f"Item {item_id}: text required")
            if status not in ("pending", "in_progress", "completed"):
                raise ValueError(f"Item {item_id}: invalid status '{status}'")
            if status == "in_progress":
                inprogress_count += 1
            validated.append({"id": item_id, "text": text, "status": status})
        if inprogress_count > 1:
            raise ValueError("Only one task can be in_progress at a time")
        self.items = validated
        return self.render_todos()


    def render_todos(self) -> str:
        """
        Render the current todo list as a string.
        Returns a string representation of the todo list.
        """
        if not self.items:
            return "No todos."
        lines = []
        for item in self.items:
            marker = {"pending": "[ ]","inprogress":"[>]","completed":"x"}[item.get("status")]
            lines.append(f"{marker} #{item.get('id')}: {item.get('text')}")
        done=sum([1 for i in self.items if i.get("status")=="completed"])
        lines.append(f"\n({done}/{len(self.items)} completed)")
        return "\n".join(lines) 
    
    