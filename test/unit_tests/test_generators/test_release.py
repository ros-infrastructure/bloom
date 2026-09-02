import os
import shutil
import tempfile
import tomli_w

try:
    import tomllib
except ImportError:
    import tomli as tomllib

from bloom.generators.release import ReleaseGenerator


class MockPackage:
    def __init__(self, build_type):
        self._build_type = build_type

    def get_build_type(self):
        return self._build_type


def test_normalize_cargo_manifest():
    # Create a temporary directory for the test
    temp_dir = tempfile.mkdtemp()
    try:
        manifest_path = os.path.join(temp_dir, 'Cargo.toml')

        # Define the original manifest content
        original_manifest = {
            'dependencies': {
                'absolute_dep': {'path': '/abs/path/to/dep'},
                'parent_dep': {'path': '../parent/dep'},
                'sibling_dep': {'path': '../sibling'},
                'subdir_dep': {'path': 'subdir/dep'},
                'dot_subdir_dep': {'path': './subdir/dep'},
                'nested_subdir_dep': {'path': 'subdir/sub2/../../subdir/sub3'},
                'not_dict_dep': '1.0.0',
            },
            'dev-dependencies': {
                'dev_parent_dep': {'path': '../dev-dep'},
                'dev_subdir_dep': {'path': 'dev-subdir'},
            },
            'build-dependencies': {
                'build_parent_dep': {'path': '../build-dep'},
                'build_subdir_dep': {'path': 'build-subdir'},
            }
        }

        # Case 1: Package of type 'cmake' (should NOT be modified or written to)
        with open(manifest_path, 'wb') as f:
            tomli_w.dump(original_manifest, f)

        # Set modification time to the past
        past_time = os.path.getmtime(manifest_path) - 100
        os.utime(manifest_path, (past_time, past_time))

        generator = ReleaseGenerator()
        generator.packages = {temp_dir: MockPackage('cmake')}

        generator._normalize_cargo_manifest(temp_dir)

        # Assert no change to content and no write (modification time remains the same)
        with open(manifest_path, 'rb') as f:
            data = tomllib.load(f)
        assert data == original_manifest
        assert os.path.getmtime(manifest_path) == past_time

        # Case 2: Package of type 'cargo' with no relative parent dependencies (should NOT be modified or written to)
        manifest_no_parent_deps = {
            'dependencies': {
                'absolute_dep': {'path': '/abs/path/to/dep'},
                'subdir_dep': {'path': 'subdir/dep'},
            }
        }
        with open(manifest_path, 'wb') as f:
            tomli_w.dump(manifest_no_parent_deps, f)

        os.utime(manifest_path, (past_time, past_time))

        generator.packages = {temp_dir: MockPackage('cargo')}
        generator._normalize_cargo_manifest(temp_dir)

        # Assert no change to content and no write (modification time remains the same)
        with open(manifest_path, 'rb') as f:
            data = tomllib.load(f)
        assert data == manifest_no_parent_deps
        assert os.path.getmtime(manifest_path) == past_time

        # Case 3: Package of type 'cargo' with parent relative dependencies (should normalize only parent relative dependencies)
        with open(manifest_path, 'wb') as f:
            tomli_w.dump(original_manifest, f)

        generator._normalize_cargo_manifest(temp_dir)

        with open(manifest_path, 'rb') as f:
            data = tomllib.load(f)

        # Let's verify each dependency after normalization
        deps = data['dependencies']
        
        # Absolute path - preserved!
        assert deps['absolute_dep']['path'] == '/abs/path/to/dep'
        assert 'version' not in deps['absolute_dep']

        # Parent referencing path - dropped and version set to *
        assert 'path' not in deps['parent_dep']
        assert deps['parent_dep']['version'] == '*'

        assert 'path' not in deps['sibling_dep']
        assert deps['sibling_dep']['version'] == '*'

        # Subdirectory path - preserved!
        assert deps['subdir_dep']['path'] == 'subdir/dep'
        assert 'version' not in deps['subdir_dep']

        assert deps['dot_subdir_dep']['path'] == './subdir/dep'
        assert 'version' not in deps['dot_subdir_dep']

        assert deps['nested_subdir_dep']['path'] == 'subdir/sub2/../../subdir/sub3'
        assert 'version' not in deps['nested_subdir_dep']

        # dev-dependencies
        dev_deps = data['dev-dependencies']
        assert 'path' not in dev_deps['dev_parent_dep']
        assert dev_deps['dev_parent_dep']['version'] == '*'
        assert dev_deps['dev_subdir_dep']['path'] == 'dev-subdir'

        # build-dependencies
        build_deps = data['build-dependencies']
        assert 'path' not in build_deps['build_parent_dep']
        assert build_deps['build_parent_dep']['version'] == '*'
        assert build_deps['build_subdir_dep']['path'] == 'build-subdir'

    finally:
        shutil.rmtree(temp_dir)
