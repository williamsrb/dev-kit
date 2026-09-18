<!-- src:https://developer.enonic.com/docs/platform/stable/security/service-accounts generated:2026-07-24T21:49:28Z format:llm-dense xp:8.x -->
#DOC docs/platform/stable/security/service-accounts.md

# Service accounts

Service accounts enable token based authentication for machine-to-machine communication with XP.

## Introduction

Service accounts are created and managed via the built-in System ID provider. They are intendend for machine-to-machine authentication from remote clients to XP.

Since service accounts are essentially regular XP users you may grant roles and permissions as needed. Service accounts users can easily be recognized from the small cog symbol above their avatar.

For a walkthrough of creating service accounts and managing keys from the UI, see the [Users admin tool](docs/platform/stable/admin/users.md#service-accounts-and-keys).

## Service Account Keys

A Service Account may be associated with one, or several Service Account keys. Using a Service Account Key is beneficial for security reasons:

- It allows to authenticate without transferring the password over the network.

- Support for multiple keys allow rotation of Public-Private key-pairs without service interruption.

- Stored Public key is not a hash of a password, so it is not possible to reverse-engineer the password from the public key.

Once a key is created, it may be used to make an authorized call to:

- The [Management Endpoint](#management_endpoint)

- Any XP engine that mounts the System ID provider. See [Virtual Hosts](https://developer.enonic.com/docs/platform/stable/deployment/vhosts.ahtml#virtual-hosts) for more details.

> **Note:** Service account keys are a security risk if not managed correctly. Make sure to rotate keys regularly and keep them safe. If you suspect that your keys have been compromised, you can revoke them in the Users app. Also consider using ID providers that support 3-leg authentication, such as the [OIDC ID provider](https://market.enonic.com/vendors/enonic/oidc-id-provider), if possible.

### Generate key

Generate keys from the [Users admin tool](docs/platform/stable/admin/users.md#service-accounts-and-keys). The public key is saved on the server, and the private key is automatically downloaded to your device in JSON format.

### Upload key

You may also upload the public key portion of a user-managed key pair, and the use the private key for authenication later.

The key you upload must be an RSA public key and encoded in base64. You can use tools such as OpenSSL to generate a key and certificate in this format.

**Try it out** The following command generates a 2048-bit RSA key pair

```terminal
openssl genpkey -algorithm RSA -out xp_private_key.pem -pkeyopt rsa_keygen_bits:2048 && \
openssl rsa -pubout -in xp_private_key.pem -out xp_public_key.pem
```

After generating the key, you may upload the `public_key.pem` file via the [Users admin tool](docs/platform/stable/admin/users.md#service-accounts-and-keys).

## JWT authentication

> **Note:** **XP enforces short-lived tokens**. You may change the default timeout of 30 seconds in [the ID provider configuration](docs/platform/stable/config/system.md#idprovider).

The System ID providers supports JWT (JSON Web Token) based authentication via the HTTP `Authorization` header.

The header should look like the following:

```
Authorization: Bearer <mytoken>
```

The JWT token must be a valid [RFC-7519](https://datatracker.ietf.org/doc/html/rfc7519) JWT token, following these requirements:

- `alg` header parameter must be set to `RS256`.

- `kid` header parameter must be set to ID of the public key that corresponds to the private key used to sign the token.

- `sub` claim must be set to ID of the service account, for instance, `user:system:myuser`.

- `exp` claim must be set to expiration time of the token. The token will be rejected if it is expired.

- `iat` claim must be set to issue time of the token. The token will be rejected if it was issued in the future.

JWT header example

```JSON
{
  "kid": "51a29c2ab5ebf945f6a5ddac8935bf8b",
  "typ": "JWT",
  "alg": "RS256"
}
```

JWT payload example

```JSON
{
  "sub": "user:system:myuser",
  "exp": 1692787396,
  "iat": 1692787366
}
```

We recommend using libraries that match your client platform to generate the token - especially related to the requirement for short lived tokens.

> **Warning:** The private key from the Public-Private key pair should only be stored on the client side to generate the token, and never shared with the XP server.

The public key from Public-Private key pair is only stored in XP, and used to verify the signature of your token.
