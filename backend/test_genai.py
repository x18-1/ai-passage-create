import sys
try:
    from google import genai
    from google.genai import types
    print("genai version:", getattr(genai, "__version__", "unknown"))
    print("Available in types for image:")
    for name in dir(types):
        if "Image" in name or "image" in name.lower() or "Config" in name:
            print(name)
except Exception as e:
    print(e)
