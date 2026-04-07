"""
Run once to generate a self-signed SSL cert for the Streamlit server.
Outputs cert.pem and key.pem in the current directory.
"""
import ipaddress
from datetime import datetime, timedelta, timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

SERVER_IP = "10.1.116.2"
DAYS_VALID = 825  # ~2 years (max Apple/browser allow for self-signed)

key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

subject = issuer = x509.Name([
    x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Citadel Health"),
    x509.NameAttribute(NameOID.COMMON_NAME, SERVER_IP),
])

cert = (
    x509.CertificateBuilder()
    .subject_name(subject)
    .issuer_name(issuer)
    .public_key(key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(datetime.now(timezone.utc))
    .not_valid_after(datetime.now(timezone.utc) + timedelta(days=DAYS_VALID))
    .add_extension(
        x509.SubjectAlternativeName([
            x509.IPAddress(ipaddress.IPv4Address(SERVER_IP)),
        ]),
        critical=False,
    )
    .sign(key, hashes.SHA256())
)

with open("cert.pem", "wb") as f:
    f.write(cert.public_bytes(serialization.Encoding.PEM))

with open("key.pem", "wb") as f:
    f.write(key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ))

print("cert.pem and key.pem generated.")
print(f"Valid for {DAYS_VALID} days.")
print()
print("Run Streamlit with:")
print("  streamlit run streamlit_app.py --server.sslCertFile cert.pem --server.sslKeyFile key.pem")
print()
print("Users will see a browser security warning on first visit.")
print("They can click 'Advanced -> Proceed' or you can install cert.pem")
print("into Windows Trusted Root Certification Authorities to suppress it.")
