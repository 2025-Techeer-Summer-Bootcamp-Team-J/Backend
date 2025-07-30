from crud.storage import download_model_from_gcs
import onnxruntime
import numpy as np
from PIL import Image
import io
from torchvision import transforms
import torch

download_model_from_gcs(
    "ppikkappeonjjeog-classifier-bucket",           # 버킷 이름
    "best_disease_classifier.onnx",          # GCS 내 파일 경로
    "best_disease_classifier.onnx"                  # 로컬에 저장할 파일명
)

# --- Configuration ---
ONNX_MODEL_PATH = 'best_disease_classifier.onnx'

# The correct, ordered list of class names based on your training map.
CLASS_NAMES = [
    'Acne', 
    'Actinic Keratosis', 
    'Atopic Dermatitis', 
    'Bacterial Infections', 
    'Basal Cell Carcinoma', 
    'Benign Keratosis', 
    "Darier's Disease", 
    'Epidermolysis Bullosa Pruriginosa', 
    'Hailey-Hailey Disease', 
    'Infestations and Bites', 
    'Leishmaniasis', 
    'Lichen Planus', 
    'Lupus', 
    'Melanocytic Nevi', 
    'Melanoma', 
    'Molluscum and Warts', 
    'Nail Fungus', 
    'Normal Skin', 
    'Porokeratosis', 
    'Psoriasis', 
    'Tinea (Ringworm)', 
    'Tungiasis', 
    'Vascular Lesions'
]

# --- ONNX Runtime Setup ---
try:
    # Create the inference session with the ONNX model.
    session = onnxruntime.InferenceSession(ONNX_MODEL_PATH)
    input_name = session.get_inputs()[0].name
    output_name = session.get_outputs()[0].name
    print(f"Successfully loaded ONNX model from {ONNX_MODEL_PATH}")
except Exception as e:
    print(f"FATAL: Error loading ONNX model. The application will not work. Error: {e}")
    session = None

# --- Image Preprocessing ---
# This must be identical to the transformations used during training.
preprocess = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

def run_onnx_inference(image_bytes):
    """
    Runs inference on the local ONNX model.
    """
    if not session:
        raise RuntimeError("ONNX model session is not available. Check for loading errors on startup.")

    try:
        # Open and preprocess the image from byte data.
        image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        image_tensor = preprocess(image).unsqueeze(0) # Add batch dimension
        image_np = image_tensor.numpy()

        # Run inference using the ONNX session.
        result = session.run([output_name], {input_name: image_np})
        
        # Post-process the model output.
        # The result is a numpy array, convert it to a torch tensor for softmax.
        probabilities = torch.nn.functional.softmax(torch.from_numpy(result[0]), dim=1)[0]
        
        # Get the top 3 predictions.
        top_k_confidences, top_k_indices = torch.topk(probabilities, 3)

        # Prepare the list of top 3 predictions.
        predictions = []
        for i in range(len(top_k_confidences)):
            confidence = top_k_confidences[i].item()
            pred_idx = top_k_indices[i].item()
            predicted_class = CLASS_NAMES[pred_idx]
            predictions.append({
                "class": predicted_class,
                "confidence": confidence
            })

        return predictions

    except Exception as e:
        # Log the error for debugging.
        print(f"Error during ONNX inference: {e}")
        # Return an empty list to indicate failure.
        return []