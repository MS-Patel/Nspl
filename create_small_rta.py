import pandas as pd

def create_small_cams():
    try:
        df = pd.read_excel("docs/rta/cams_WBR2.xls")
        df.columns = df.columns.str.lower()

        target_txn = "220265247"
        small_df = df[df['trxnno'].astype(str) == target_txn]

        if small_df.empty:
            print("Target txn not found in CAMS file")
            return

        print(f"Found {len(small_df)} rows for CAMS txn {target_txn}")
        small_df.to_excel("docs/rta/small_cams.xlsx", index=False)
        print("Created docs/rta/small_cams.xlsx")
    except Exception as e:
        print(f"Error creating small CAMS: {e}")

def create_small_karvy():
    try:
        df = pd.read_excel("docs/rta/karvy_MFSD201.xls", header=1)
        df.columns = df.columns.str.lower()

        target_txn = "682020979"
        small_df = df[df['td_trno'].astype(str) == target_txn]

        if small_df.empty:
            print("Target txn not found in Karvy file")
            return

        print(f"Found {len(small_df)} rows for Karvy txn {target_txn}")

        # Write with dummy header for Karvy parser (skips row 0)
        with pd.ExcelWriter("docs/rta/small_karvy.xlsx", engine='openpyxl') as writer:
            pd.DataFrame(["Dummy Header"]).to_excel(writer, startrow=0, index=False, header=False)
            small_df.to_excel(writer, startrow=1, index=False)

        print("Created docs/rta/small_karvy.xlsx with dummy header row")
    except Exception as e:
        print(f"Error creating small Karvy: {e}")

if __name__ == "__main__":
    create_small_cams()
    create_small_karvy()
