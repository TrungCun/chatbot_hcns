"""
Test EmbedTools: dense + sparse + hybrid embedding.
Chạy: conda run -n chatbothcns python test_embed.py
"""
import time

def main():
    print("=" * 60)
    print("TEST EMBED TOOLS")
    print("=" * 60)

    # 1. Load models
    print("\n[1] Loading models...")
    start = time.perf_counter()
    from app.application import application
    application.load_models()
    print(f"    Load time: {(time.perf_counter() - start) * 1000:.0f} ms")

    from app.tools.embed import EmbedTools

    # 2. Embedding dimension
    print("\n[2] Embedding dimension...")
    dim = EmbedTools.get_embedding_dimension()
    print(f"    Dense dim: {dim}")
    assert dim == 1024, f"Expected 1024, got {dim}"
    print("    OK")

    # 3. Dense single
    print("\n[3] Dense single encode...")
    text = "Chính sách nghỉ phép năm dành cho nhân viên toàn thời gian"
    dense = EmbedTools.compute_dense_vector(text)
    print(f"    Input : '{text}'")
    print(f"    Output: dim={len(dense)}, sample={[round(v, 4) for v in dense[:5]]}")
    assert len(dense) == 1024
    print("    OK")

    # 4. Sparse single
    print("\n[4] Sparse single encode...")
    indices, values = EmbedTools.compute_sparse_vector(text)
    print(f"    Nonzero tokens : {len(indices)}")
    print(f"    Sample indices : {indices[:5]}")
    print(f"    Sample values  : {[round(v, 4) for v in values[:5]]}")
    assert len(indices) > 0
    print("    OK")

    # 5. Hybrid query
    print("\n[5] Hybrid query embed...")
    dense2, idx2, val2 = EmbedTools.hybrid_embed_query(text)
    print(f"    Dense dim     : {len(dense2)}")
    print(f"    Sparse nonzero: {len(idx2)}")
    print("    OK")

    # 6. Batch encode
    print("\n[6] Batch encode (5 texts)...")
    texts = [
        "Chính sách nghỉ phép năm",
        "Quy định về tăng ca và làm thêm giờ",
        "Bảo hiểm xã hội và bảo hiểm y tế",
        "Quy trình đánh giá nhân viên hàng năm",
        "Chính sách lương thưởng theo hiệu suất",
    ]
    dense_vecs, sparse_vecs = EmbedTools.hybrid_embed_batch(texts, batch_size=5)
    print(f"    Texts        : {len(texts)}")
    print(f"    Dense output : {len(dense_vecs)} vectors x {len(dense_vecs[0])}d")
    print(f"    Sparse output: {len(sparse_vecs)} vectors")
    for i, (idx, val) in enumerate(sparse_vecs):
        print(f"      [{i}] nonzero={len(idx)}")
    assert len(dense_vecs) == len(texts)
    assert len(sparse_vecs) == len(texts)
    print("    OK")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
