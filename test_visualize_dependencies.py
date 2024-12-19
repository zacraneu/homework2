import unittest
from unittest.mock import patch, mock_open, MagicMock
import json
import subprocess
import sys
import os
import requests  # Добавьте импорт requests

# Убедитесь, что путь корректно добавлен
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))  # Путь к текущей директории

from visualize_dependencies import (
    fetch_package_info,
    build_dependencies_tree,
    generate_graph,
    save_graph_to_file,
    generate_graph_image,
    main
)

class TestVisualizeDependency(unittest.TestCase):

    # Тестируем функцию fetch_package_info
    @patch("requests.get")
    def test_fetch_package_info_latest_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.side_effect = [
            {"dist-tags": {"latest": "1.0.0"}},
            {"name": "packageA", "version": "1.0.0", "dependencies": {"packageB": "^2.0.0"}}
        ]
        mock_get.return_value = mock_response

        result = fetch_package_info("packageA", "latest", "https://registry.npmjs.org")
        expected = {"name": "packageA", "version": "1.0.0", "dependencies": {"packageB": "^2.0.0"}}
        self.assertEqual(result, expected)
        self.assertEqual(mock_get.call_count, 2)
        mock_get.assert_any_call("https://registry.npmjs.org/packageA")
        mock_get.assert_any_call("https://registry.npmjs.org/packageA/1.0.0")

    @patch("requests.get")
    def test_fetch_package_info_specific_version_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"name": "packageA", "version": "1.0.0", "dependencies": {"packageB": "^2.0.0"}}
        mock_get.return_value = mock_response

        result = fetch_package_info("packageA", "1.0.0", "https://registry.npmjs.org")
        expected = {"name": "packageA", "version": "1.0.0", "dependencies": {"packageB": "^2.0.0"}}
        self.assertEqual(result, expected)
        mock_get.assert_called_once_with("https://registry.npmjs.org/packageA/1.0.0")

    @patch("requests.get")
    def test_fetch_package_info_failure(self, mock_get):
        mock_get.side_effect = requests.RequestException("Not Found")
        result = fetch_package_info("nonexistent-package", "latest", "https://registry.npmjs.org")
        self.assertEqual(result, {})
        mock_get.assert_called_once_with("https://registry.npmjs.org/nonexistent-package")

    

    @patch("visualize_dependencies.fetch_package_info")
    def test_build_dependencies_tree_max_depth(self, mock_fetch_package_info):
        # Настраиваем моки для пакетов
        mock_fetch_package_info.side_effect = [
            {"dependencies": {"packageB": "^2.0.0"}},
            {"dependencies": {"packageC": "^3.0.0"}},
            {"dependencies": {}}
        ]

        result = build_dependencies_tree("packageA", "1.0.0", 1, 1, "https://registry.npmjs.org")
        expected = {
            "packageA@1.0.0": ["packageB@latest"]
        }
        self.assertEqual(result, expected)
        mock_fetch_package_info.assert_called_once_with("packageA", "1.0.0", "https://registry.npmjs.org")

    @patch("visualize_dependencies.fetch_package_info")
    def test_build_dependencies_tree_cycle(self, mock_fetch_package_info):
        # Настраиваем моки для пакетов, создавая цикл: packageA -> packageB -> packageA
        mock_fetch_package_info.side_effect = [
            {"dependencies": {"packageB": "^2.0.0"}},  # packageA@1.0.0
            {"dependencies": {"packageA": "^1.0.0"}},  # packageB@latest
            {"dependencies": {"packageB": "^2.0.0"}},  # packageA@latest
        ]

        result = build_dependencies_tree("packageA", "1.0.0", 1, 3, "https://registry.npmjs.org")
        expected = {
            "packageA@1.0.0": ["packageB@latest"],
            "packageB@latest": ["packageA@latest"],
            "packageA@latest": ["packageB@latest"]
        }
        self.assertEqual(result, expected)
        self.assertEqual(mock_fetch_package_info.call_count, 3)
        mock_fetch_package_info.assert_any_call("packageA", "1.0.0", "https://registry.npmjs.org")
        mock_fetch_package_info.assert_any_call("packageB", "latest", "https://registry.npmjs.org")
        mock_fetch_package_info.assert_any_call("packageA", "latest", "https://registry.npmjs.org")

    # Тестируем функцию save_graph_to_file
    @patch("builtins.open", new_callable=mock_open)
    def test_save_graph_to_file_success(self, mock_file):
        graph_code = """digraph dependencies {
      node [shape=box];
      "packageA@1.0.0" -> "packageB@latest";
    }
    """
        save_graph_to_file(graph_code, "output.dot")
        mock_file.assert_called_once_with("output.dot", 'w', encoding='utf-8')
        mock_file().write.assert_called_once_with(graph_code)

    @patch("builtins.open", new_callable=mock_open)
    def test_save_graph_to_file_failure(self, mock_file):
        mock_file.side_effect = Exception("Cannot write file")
        graph_code = "invalid graph"
        with self.assertRaises(Exception) as context:
            save_graph_to_file(graph_code, "output.dot")
        self.assertIn("Ошибка при сохранении графа в output.dot: Cannot write file", str(context.exception))

    # Тестируем функцию generate_graph_image
    @patch("subprocess.run")
    def test_generate_graph_image_success(self, mock_subprocess_run):
        mock_subprocess_run.return_value = None
        visualizer_path = "/path/to/graphviz"
        output_file = "output.dot"
        image_file = "output.png"
        generate_graph_image(visualizer_path, output_file, image_file)
        mock_subprocess_run.assert_called_once_with(
            [visualizer_path, '-Tpng', output_file, '-o', image_file],
            check=True
        )

    @patch("subprocess.run")
    def test_generate_graph_image_failure(self, mock_subprocess_run):
        mock_subprocess_run.side_effect = subprocess.CalledProcessError(1, ['dot'])
        visualizer_path = "/path/to/graphviz"
        output_file = "output.dot"
        image_file = "output.png"
        with self.assertRaises(Exception) as context:
            generate_graph_image(visualizer_path, output_file, image_file)
        self.assertIn("Ошибка при генерации изображения графа", str(context.exception))

    # Тестируем основную функцию main
    @patch("visualize_dependencies.generate_graph_image")
    @patch("visualize_dependencies.save_graph_to_file")
    @patch("visualize_dependencies.generate_graph")
    @patch("visualize_dependencies.build_dependencies_tree")
    @patch("visualize_dependencies.fetch_package_info")
    @patch("builtins.print")
    def test_main_success(self, mock_print, mock_fetch_package_info, mock_build_dependencies_tree,
                          mock_generate_graph, mock_save_graph_to_file, mock_generate_graph_image):
        # Настраиваем моки
        mock_build_dependencies_tree.return_value = {
            "express@latest": ["packageB@latest", "packageC@latest"],
            "packageB@latest": [],
            "packageC@latest": []
        }
        mock_generate_graph.return_value = """digraph dependencies {
      node [shape=box];
      "express@latest" -> "packageB@latest";
      "express@latest" -> "packageC@latest";
    }
    """
        
        # Настраиваем аргументы командной строки
        test_args = ["script_name", "/path/to/dot.exe", "express", "output.dot", "3", "https://registry.npmjs.org"]
        with patch.object(sys, 'argv', test_args):
            main()
        
        # Проверяем вызовы
        mock_build_dependencies_tree.assert_called_once_with("express", "latest", 1, 3, "https://registry.npmjs.org")
        mock_generate_graph.assert_called_once_with({
            "express@latest": ["packageB@latest", "packageC@latest"],
            "packageB@latest": [],
            "packageC@latest": []
        })
        mock_save_graph_to_file.assert_called_once_with("""digraph dependencies {
      node [shape=box];
      "express@latest" -> "packageB@latest";
      "express@latest" -> "packageC@latest";
    }
    """, "output.dot")
        mock_generate_graph_image.assert_called_once_with("/path/to/dot.exe", "output.dot", "output.png")
        mock_print.assert_any_call("Graph успешно сгенерирован! Изображение сохранено в output.png")

    @patch("builtins.print")
    def test_main_invalid_arguments(self, mock_print):
        test_args = ["script_name", "/path/to/dot.exe", "express", "output.dot"]  # Недостаточно аргументов
        with patch.object(sys, 'argv', test_args):
            with self.assertRaises(SystemExit) as cm:
                main()
            self.assertEqual(cm.exception.code, 1)
            mock_print.assert_any_call("Usage: python visualize_dependencies.py <path_to_dot> <package_name> <output_dot_file> <max_depth> <registry_url>")
            mock_print.assert_any_call('Example:')
            mock_print.assert_any_call('python visualize_dependencies.py "C:/Program Files/Graphviz/bin/dot.exe" express output.dot 3 https://registry.npmjs.org')

    @patch("visualize_dependencies.build_dependencies_tree")
    @patch("builtins.print")
    def test_main_no_dependencies(self, mock_print, mock_build_dependencies_tree):
        mock_build_dependencies_tree.return_value = {}
        test_args = ["script_name", "/path/to/dot.exe", "express", "output.dot", "3", "https://registry.npmjs.org"]
        with patch.object(sys, 'argv', test_args):
            with self.assertRaises(SystemExit) as cm:
                main()
            self.assertEqual(cm.exception.code, 0)
            mock_print.assert_any_call("Нет зависимостей для пакета 'express'.")

    @patch("visualize_dependencies.build_dependencies_tree", side_effect=Exception("Fetch error"))
    @patch("builtins.print")
    def test_main_exception(self, mock_print, mock_build_dependencies_tree):
        test_args = ["script_name", "/path/to/dot.exe", "express", "output.dot", "3", "https://registry.npmjs.org"]
        with patch.object(sys, 'argv', test_args):
            with self.assertRaises(SystemExit) as cm:
                main()
            self.assertEqual(cm.exception.code, 1)
            mock_print.assert_any_call("Error: Fetch error")


if __name__ == "__main__":
    unittest.main()
