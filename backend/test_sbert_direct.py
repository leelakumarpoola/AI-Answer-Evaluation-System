from sentence_transformers import SentenceTransformer, util
import sys

def run_tests():
    try:
        model = SentenceTransformer("all-MiniLM-L6-v2")
    except Exception as e:
        print(f"Failed to load model: {e}")
        sys.exit(1)
        
    print("Model loaded successfully")
    
    # Test 1: High similarity
    ans1_student = "Blockchain is a decentralized distributed ledger where transactions are recorded across multiple computers."
    ans1_model = "Blockchain is a distributed ledger technology that stores transactions across multiple nodes without depending on a central authority."
    
    emb1_s = model.encode(ans1_student, convert_to_tensor=True)
    emb1_m = model.encode(ans1_model, convert_to_tensor=True)
    sim1 = util.cos_sim(emb1_s, emb1_m)[0][0].item()
    print(f"Test 1 (High similarity): {sim1:.4f}")
    assert sim1 > 0.6, "Similarity should be relatively high"
    
    # Test 2: Low similarity
    ans2_student = "A compiler translates source code into machine code."
    ans2_model = "Blockchain is a distributed ledger maintained across a network of nodes."
    
    emb2_s = model.encode(ans2_student, convert_to_tensor=True)
    emb2_m = model.encode(ans2_model, convert_to_tensor=True)
    sim2 = util.cos_sim(emb2_s, emb2_m)[0][0].item()
    print(f"Test 2 (Low similarity): {sim2:.4f}")
    assert sim2 < 0.4, "Similarity should be relatively low"
    
    print("SBERT Direct Tests Passed!")
    
if __name__ == "__main__":
    run_tests()
