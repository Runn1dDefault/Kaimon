def import_model(model_import_path: str):
    assert '.' in model_import_path

    package = model_import_path.split('.')
    model_name = package[-1]
    mod = __import__('.'.join(package[:-1]), fromlist=[model_name])
    return getattr(mod, model_name)
