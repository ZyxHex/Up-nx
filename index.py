from app import app
from flask import jsonify

@app.route('/')
def index():
    return jsonify({"message": "ZYXX GEN API", "status": "active"})

if __name__ == '__main__':
    app.run()
