import sys
print("Python:", sys.version, flush=True)
print("Importing torch...", flush=True)
import torch
print("PyTorch:", torch.__version__, flush=True)
print("CUDA available:", torch.cuda.is_available(), flush=True)
if torch.cuda.is_available():
    print("CUDA version:", torch.version.cuda, flush=True)
    print("GPU:", torch.cuda.get_device_name(0), flush=True)
    print("GPU Memory:", round(torch.cuda.get_device_properties(0).total_mem / 1024**3, 1), "GB", flush=True)
    # Quick test
    x = torch.randn(1000, 1000, device='cuda')
    y = torch.matmul(x, x)
    print("CUDA computation test: OK", flush=True)
else:
    print("CUDA NOT available!", flush=True)
    print("Reason: torch was built without CUDA or drivers not compatible", flush=True)
