import torch
print(torch.cuda.is_available())      # True ✅
print(torch.cuda.get_device_name(0))  # NVIDIA GeForce RTX 3050 ✅
print(torch.__version__)              # 2.x.x+cu124 ✅