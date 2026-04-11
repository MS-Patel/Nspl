1. **Add a `change_password` method to `BSEStarMFClient` (`apps/integration/bse_client.py`)**:
   - The method will accept the `new_password` as an argument.
   - It will authenticate with the query client (`_get_query_auth_details`) to get the encrypted old password.
   - It will use the `MFAPI` service on the query client.
   - The parameters for `MFAPI` will be `Flag='04'`, `UserId=self.user_id`, `EncryptedPassword=encrypted_password`, and `param=f"{self.password}|{new_password}|{new_password}"`.
   - It will format the response similarly to other methods, returning `{'status': 'success', 'remarks': ...}` or `{'status': 'error', 'remarks': ...}`.

2. **Add a Django management command to automate this (`apps/integration/management/commands/change_bse_password.py`)**:
   - This script can be run manually or set up in a cron job.
   - It will parse the new password as an argument.
   - It will call `bse_client.change_password(new_password)`.
   - Upon success, it will suggest (via a print statement) updating the `.env` file or environment variables with the new password, as the application needs the new password to continue functioning.

3. **Pre-commit Instructions**:
   - Run pre-commit instructions to make sure code verification, checks, tests are done correctly.

4. **Submit**:
   - Review the diff, commit the changes to a new branch, and submit.
