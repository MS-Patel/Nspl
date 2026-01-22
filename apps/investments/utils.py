import time
import random
import string

def generate_distributor_based_ref(distributor_id):
    """
    Generates a unique reference number embedding the Distributor ID.
    Format: {DistributorID:06d}{TimestampSec:10d}{Random:03d}
    Total Length: 19 characters.
    Example: 0000051705622400123
    """
    if distributor_id is None:
        distributor_id = 0

    # Ensure Distributor ID fits in 6 chars
    dist_str = f"{distributor_id:06d}"

    # Timestamp in seconds (10 digits for current epoch)
    timestamp = int(time.time())

    # 3 random digits
    rand_suffix = ''.join(random.choices(string.digits, k=3))

    return f"{dist_str}{timestamp}{rand_suffix}"
