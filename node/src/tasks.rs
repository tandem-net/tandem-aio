use futures::future::BoxFuture;
use reqwest::{Client, Error};
use crate::measure;

pub fn download_task(client: Client, url: impl Into<String>) -> BoxFuture<'static, Result<(), Error>> {
    let url = url.into();

    Box::pin(async move {
        let (bytes, duration) = measure::measure_download(client, &url).await?;
        let mb = bytes as f64 / (1024.0 * 1024.0);
        println!("downloaded {:.2} MB in {:.2}s ({:.2} MB/s)", mb, duration, mb / duration);
        Ok(())
    })
}

pub fn upload_task(client: Client, url: impl Into<String>, bytes: usize) -> BoxFuture<'static, Result<(), Error>> {
    let url = url.into();

    Box::pin(async move {
        let duration = measure::measure_upload(client, &url, bytes, 65536).await?;
        let mb = bytes as f64 / (1024.0 * 1024.0);

        println!("uploaded {:.2} MB in {:.2}s ({:.2} MB/s", mb, duration, mb / duration);
        Ok(())
    })
}