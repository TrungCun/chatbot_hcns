import pandas as pd
df = pd.read_csv("stress_test_multiturn_report.csv")

print("=== THỜI GIAN TRUNG BÌNH ===")
print(f"Chit-chat: {df[df['Domain'] == 'chitchat']['Time (s)'].mean():.2f} s")
print(f"Job (SQL): {df[df['Domain'] == 'job']['Time (s)'].mean():.2f} s")
print(f"Company/Policy (RAG): {df[df['Domain'].isin(['company', 'policy'])]['Time (s)'].mean():.2f} s")
print(f"Overall: {df['Time (s)'].mean():.2f} s")

print("\n=== CHI TIẾT CÁC CÂU BỊ FAIL ===")
fail_df = df[df["Result"] == "FAIL"]
for i, row in fail_df.iterrows():
    print(f"Turn {row['Turn']}: {row['Question']}")
    print(f"Domain: {row['Domain']}")
    print(f"Lý do:\n{row['Reason']}\n")
    print("-" * 50)
