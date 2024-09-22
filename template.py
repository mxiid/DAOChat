import os
import shutil

def create_directory(path):
    os.makedirs(path, exist_ok=True)

def create_file(path, content=''):
    with open(path, 'w') as f:
        f.write(content)

def create_project_structure():
    # Create main directories
    create_directory('backend')
    create_directory('frontend')
    create_directory('nginx')
    create_directory('traefik')

    # Create backend structure
    create_directory('backend/app')
    create_directory('backend/app/api')
    create_directory('backend/tests')

    # Create backend files
    create_file('backend/app/__init__.py')
    create_file('backend/app/main.py')
    create_file('backend/app/config.py')
    create_file('backend/app/models.py')
    create_file('backend/app/database.py')
    create_file('backend/app/vector_store.py')
    create_file('backend/app/rag.py')
    create_file('backend/app/api/__init__.py')
    create_file('backend/app/api/routes.py')
    create_file('backend/tests/test_api.py')
    create_file('backend/Dockerfile')
    create_file('backend/requirements.txt')

    # Create frontend structure
    create_directory('frontend/public')
    create_directory('frontend/src')
    create_directory('frontend/src/components')
    create_directory('frontend/src/pages')
    create_directory('frontend/src/styles')
    create_directory('frontend/src/utils')

    # Create frontend files
    create_file('frontend/src/App.js')
    create_file('frontend/src/index.js')
    create_file('frontend/package.json')
    create_file('frontend/Dockerfile')

    # Create nginx and traefik files
    create_file('nginx/nginx.conf')
    create_file('traefik/traefik.yml')

    # Create root files
    create_file('docker-compose.yml')
    create_file('README.md')
    create_file('.env')

def main():
    create_project_structure()
    print("Project structure created successfully!")

if __name__ == "__main__":
    main()
