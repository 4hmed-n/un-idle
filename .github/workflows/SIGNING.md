# Code Signing Placeholder

Code signing is not currently implemented but can be added using the following approach:

## Windows Code Signing

To sign the Windows executable, add this step after the PyInstaller build in `build.yml`:

```yaml
- name: Sign Windows Executable
  if: startsWith(github.ref, 'refs/tags/v')
  run: |
    # Install signtool (part of Windows SDK)
    # Option 1: Use Azure Key Vault for certificate storage
    # Option 2: Use GitHub encrypted secrets for certificate
    
    # Example with certificate file:
    # echo "${{ secrets.WINDOWS_CERT_BASE64 }}" | base64 --decode > cert.pfx
    # signtool sign /f cert.pfx /p "${{ secrets.CERT_PASSWORD }}" /t http://timestamp.digicert.com /fd SHA256 dist/un-idle.exe
    # rm cert.pfx
    
    # Verify signature:
    # signtool verify /pa dist/un-idle.exe
```

## Requirements

1. **Certificate**: Obtain a code signing certificate from a trusted CA
2. **Secure Storage**: Store certificate in GitHub secrets (base64 encoded) or Azure Key Vault
3. **Timestamp Server**: Use a trusted timestamp server (e.g., DigiCert, Sectigo)
4. **Verification**: Always verify the signature after signing

## Notes

- Code signing requires a valid certificate from a trusted Certificate Authority
- Certificates typically cost $100-400/year
- EV (Extended Validation) certificates provide immediate SmartScreen reputation
- Standard certificates require building reputation over time
- Never commit certificates or private keys to the repository
