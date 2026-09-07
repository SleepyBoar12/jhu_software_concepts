from board import create_app

### Use this to run the program and create the app!

app = create_app()

if __name__ == "__main__":
    app.run(host = "localhost", port = 8080, debug=True)