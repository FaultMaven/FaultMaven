"""S3-compatible storage provider for Enterprise profile."""

from typing import Optional
import aioboto3
from botocore.exceptions import ClientError

from faultmaven.providers.interfaces import FileProvider


class S3FileProvider(FileProvider):
    """
    S3-compatible implementation of FileProvider.

    Works with AWS S3, MinIO, or other S3-compatible object stores.
    """

    def __init__(
        self,
        bucket: str,
        region: str = "us-east-1",
        endpoint_url: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
    ):
        """
        Initialize S3 file provider.

        Args:
            bucket: S3 bucket name
            region: AWS region
            endpoint_url: Custom endpoint URL (for MinIO, etc.)
            aws_access_key_id: AWS access key (optional, can use env/IAM)
            aws_secret_access_key: AWS secret key (optional, can use env/IAM)
        """
        self.bucket = bucket
        self.region = region
        self.endpoint_url = endpoint_url

        self.session = aioboto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region,
        )

    async def upload(
        self,
        key: str,
        data: bytes,
        content_type: str,
        metadata: Optional[dict[str, str]] = None,
    ) -> str:
        """Upload file to S3."""
        async with self.session.client("s3", endpoint_url=self.endpoint_url) as s3:
            await s3.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
                Metadata=metadata or {},
            )

        return f"s3://{self.bucket}/{key}"

    async def download(self, key: str) -> bytes:
        """Download file from S3."""
        async with self.session.client("s3", endpoint_url=self.endpoint_url) as s3:
            try:
                response = await s3.get_object(Bucket=self.bucket, Key=key)
                async with response["Body"] as stream:
                    return await stream.read()
            except ClientError as e:
                if e.response["Error"]["Code"] == "NoSuchKey":
                    raise FileNotFoundError(f"File not found: {key}")
                raise

    async def delete(self, key: str) -> bool:
        """Delete file from S3."""
        async with self.session.client("s3", endpoint_url=self.endpoint_url) as s3:
            try:
                await s3.delete_object(Bucket=self.bucket, Key=key)
                return True
            except ClientError:
                return False

    async def get_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate presigned URL for S3 object."""
        async with self.session.client("s3", endpoint_url=self.endpoint_url) as s3:
            url = await s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires_in,
            )
            return url

    async def exists(self, key: str) -> bool:
        """Check if file exists in S3."""
        async with self.session.client("s3", endpoint_url=self.endpoint_url) as s3:
            try:
                await s3.head_object(Bucket=self.bucket, Key=key)
                return True
            except ClientError:
                return False
