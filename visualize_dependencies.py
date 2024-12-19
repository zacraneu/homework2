import json
import sys
import subprocess
import requests  # Необходимо установить через pip: pip install requests
from urllib.parse import urlparse

def fetch_package_info(package_name, version='latest', registry_url='https://registry.npmjs.org'):
    """
    Получает информацию о пакете из npm Registry.

    :param package_name: Название пакета.
    :param version: Версия пакета (по умолчанию latest).
    :param registry_url: URL npm Registry.
    :return: Словарь с информацией о пакете.
    """
    try:
        if version == 'latest':
            url = f"{registry_url}/{package_name}"
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            latest_version = data.get('dist-tags', {}).get('latest')
            if not latest_version:
                print(f"Предупреждение: Не удалось определить последнюю версию для пакета '{package_name}'.")
                return {}
            url = f"{registry_url}/{package_name}/{latest_version}"
        else:
            url = f"{registry_url}/{package_name}/{version}"
        
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Предупреждение: Не удалось получить информацию о пакете '{package_name}': {e}")
        return {}

def build_dependencies_tree(package_name, version, depth, max_depth, registry_url, tree=None, visited=None):
    """
    Рекурсивно строит дерево зависимостей.

    :param package_name: Название пакета.
    :param version: Версия пакета.
    :param depth: Текущая глубина рекурсии.
    :param max_depth: Максимальная глубина рекурсии.
    :param registry_url: URL npm Registry.
    :param tree: Текущее дерево зависимостей.
    :param visited: Множество уже посещённых пакетов для предотвращения циклов.
    :return: Обновлённое дерево зависимостей.
    """
    if tree is None:
        tree = {}
    if visited is None:
        visited = set()

    if depth > max_depth:
        return tree

    package_key = f"{package_name}@{version}"
    if package_key in visited:
        return tree
    visited.add(package_key)

    package_info = fetch_package_info(package_name, version, registry_url)
    dependencies = package_info.get('dependencies', {})
    tree[package_key] = []

    for dep, dep_version_range in dependencies.items():
        # Для упрощения используем 'latest' вместо точной версии из диапазона
        dep_version = 'latest'
        dep_key = f"{dep}@{dep_version}"
        tree[package_key].append(dep_key)
        build_dependencies_tree(dep, dep_version, depth + 1, max_depth, registry_url, tree, visited)

    return tree

def generate_graph(dependencies):
    """
    Генерирует строку в формате Graphviz для визуализации зависимостей.

    :param dependencies: Словарь зависимостей.
    :return: Строка Graphviz.
    """
    graph = "digraph dependencies {\n"
    graph += "  node [shape=box];\n"
    for dep, sub_deps in dependencies.items():
        for sub_dep in sub_deps:
            graph += f'  "{dep}" -> "{sub_dep}";\n'
    graph += "}\n"
    return graph

def save_graph_to_file(graph_code, output_file):
    """
    Сохраняет код Graphviz в файл.

    :param graph_code: Строка Graphviz.
    :param output_file: Путь к выходному `.dot` файлу.
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(graph_code)
        print(f"Graphviz код сохранён в {output_file}")
    except Exception as e:
        raise Exception(f"Ошибка при сохранении графа в {output_file}: {e}")

def generate_graph_image(visualizer_path, output_file, image_file):
    """
    Визуализирует граф с помощью Graphviz (dot).

    :param visualizer_path: Путь к исполняемому файлу `dot`.
    :param output_file: Путь к `.dot` файлу.
    :param image_file: Путь к выходному изображению (например, `.png`).
    """
    try:
        print(f"Генерация изображения графа в {image_file}...")
        subprocess.run([visualizer_path, '-Tpng', output_file, '-o', image_file], check=True)
        print(f"Изображение графа сохранено в {image_file}")
    except subprocess.CalledProcessError as e:
        raise Exception(f"Ошибка при генерации изображения графа: {e}")

def main():
    """
    Основная функция для работы с командной строкой.
    """
    if len(sys.argv) != 6:
        print("Usage: python visualize_dependencies.py <path_to_dot> <package_name> <output_dot_file> <max_depth> <registry_url>")
        print("Example:")
        print('python visualize_dependencies.py "C:/Program Files/Graphviz/bin/dot.exe" express output.dot 3 https://registry.npmjs.org')
        sys.exit(1)

    visualizer_path = sys.argv[1]
    package_name = sys.argv[2]
    output_file = sys.argv[3]
    try:
        max_depth = int(sys.argv[4])
    except ValueError:
        print("Error: <max_depth> должен быть целым числом.")
        sys.exit(1)
    registry_url = sys.argv[5].rstrip('/')  # Удаляем возможный слэш в конце

    try:
        print(f"Извлечение зависимостей для пакета '{package_name}' до глубины {max_depth}...")
        dependencies_tree = build_dependencies_tree(package_name, 'latest', 1, max_depth, registry_url)
        
        if not dependencies_tree:
            print(f"Нет зависимостей для пакета '{package_name}'.")
            sys.exit(0)
        
        # Генерируем код Graphviz
        print("Генерация Graphviz кода...")
        graph_code = generate_graph(dependencies_tree)

        # Сохраняем код в файл
        save_graph_to_file(graph_code, output_file)

        # Генерируем изображение
        image_file = output_file.replace('.dot', '.png')
        generate_graph_image(visualizer_path, output_file, image_file)

        print(f"Graph успешно сгенерирован! Изображение сохранено в {image_file}")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
