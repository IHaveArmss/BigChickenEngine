from engine import GraphicsEngine

if __name__ == '__main__':
    app = GraphicsEngine()
    try:
        app.run()
    except KeyboardInterrupt:
        pass