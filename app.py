import os
from flask import Flask

# Import Blueprint dari folder routes
from routes.auth import auth_bp
from routes.keuangan import keuangan_bp
from routes.ai import ai_bp

app = Flask(__name__)

# Konfigurasi aplikasi
app.secret_key = os.environ.get("SECRET_KEY")

# Daftarkan semua routes
app.register_blueprint(auth_bp)
app.register_blueprint(keuangan_bp)
app.register_blueprint(ai_bp)

if __name__ == '__main__':
    app.run(debug=True)