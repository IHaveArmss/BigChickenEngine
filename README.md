![Big Chicken Engine Banner](assets/banner.png)

# 🐔 Big Chicken Engine

**Big Chicken Engine** is a high-performance, Python-based 3D game engine and editor designed for rapid prototyping and seamless development. Powered by **ModernGL** for rendering and **PyBullet** for physics, it offers a robust environment for creating interactive 3D experiences.

---

## 🚀 Features
#
- **🎮 Dual Mode Workflow**: 
  - **Dev Mode**: Real-time scene editing, object manipulation, and hierarchy management.
  - **Play Mode**: Instant runtime execution with full physics and script processing.
- **🐍 Python Scripting**: Attach modular Python scripts to any game object for custom logic and behaviors.
- **⚡ Advanced Rendering**: ModernGL-based pipeline featuring:
  - Dynamic lighting and shadows (Phong shading).
  - Skinned mesh animation support.
  - Post-processing effects.
- **🧱 Physics & Collisions**: Integrated PyBullet engine for stable rigid body dynamics and collision detection.
- **📁 Scene & Prefab System**: JSON-based scene and prefab formats for easy versioning and sharing.
- **🛠️ Built-in Editor**: intuitive UI for transforming objects, adjusting settings, and managing assets.

---

## 🛠️ Quick Start

### Prerequisites
- Python 3.10+
- OpenGL 3.3+ capable GPU/Drivers

### Installation
```bash
git clone https://github.com/IHaveArmss/BigChickenEngine.git
cd BigChickenEngine
pip install -r requirements.txt
```

### Run
```bash
python main.py
```

---

## ⌨️ Controls

| Key | Action |
| :--- | :--- |
| **`F1`** | Toggle Dev Mode (Editor) / Play Mode (Runtime) |
| **`F2`** | Toggle Cursor Mode (UI) / FPS Camera Control |
| **`F3`** | Toggle Scene Hierarchy Panel |
| **`Ctrl + S`** | Save Current Scene |
| **`Delete`** | Remove Selected Object (Dev Mode) |
| **`H`** | Toggle In-Game Help Overlay |
| **`Esc`** | Exit current mode or quit application |

### FPS Camera Controls
*When cursor is locked:*
- **`W / A / S / D`**: Movement
- **`Space / L-Shift`**: Fly Up / Down
- **Mouse**: Look Around

---

## 📚 Documentation

Dive deeper into the engine's capabilities:

- [Getting Started Guide](docs/getting_started.md) - Build your first scene.
- [Dev Mode Guide](docs/dev_mode_guide.md) - Master the editor tools.
- [Scripting Manual](docs/scripting_guide.md) - API reference and examples.
- [Engine Architecture](docs/engine_architecture.md) - Under the hood technical details.
- [Troubleshooting](docs/troubleshooting.md) - Common fixes and tips.

---

## 📂 Project Structure

```text
BigChickenEngine/
├── main.py           # Entry point
├── engine.py         # Main engine loop and coordination
├── core/             # Essential engine modules (Renderer, Physics, etc.)
├── shaders/          # GLSL shader files
├── scenes/           # JSON scene definitions
├── scripts/          # Python behavior scripts
├── assets/           # 3D Models, textures, and audio
├── prefabs/          # Reusable object templates
└── docs/             # Comprehensive documentation
```

---

*Built with passion for 3D development by the Big Chicken Team.*