import requests
import time

def test_prediction():
    url = "http://localhost:8000/predict"
    payload = {
        "sepal_length": 5.1,
        "sepal_width": 3.5,
        "petal_length": 1.4,
        "petal_width": 0.2
    }
    
    print("Testing API...")
    start_time = time.time()
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        end_time = time.time()
        
        print("Success!")
        print(f"Status Code: {response.status_code}")
        print(f"Response Body: {response.json()}")
        print(f"Latency: {(end_time - start_time) * 1000:.2f} ms")
    except requests.exceptions.RequestException as e:
        print(f"Error testing API: {e}")

if __name__ == "__main__":
    test_prediction()
