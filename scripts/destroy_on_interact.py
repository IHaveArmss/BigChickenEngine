class DestroyOnInteract:
    def start(self):
        pass

    def on_interact(self):
        if self.entity in self.engine.scene_objects:
            idx = self.engine.scene_objects.index(self.entity)
            
            for m in self.entity.meshes:
                m.destroy()
            
            self.engine.scene_objects.pop(idx)
            self.engine.selected_index = -1
            self.engine._rebuild_renderables()
            print(f"[DestroyOnInteract] Destroyed '{self.entity.name}'")
        
        return None
