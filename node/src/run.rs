use std::result::Result;
use std::error::Error;
use wasmtime::{Engine, Module, Store, Instance};

pub fn main() -> Result<(), Box<dyn Error>> {
    let engine = Engine::default();

    let module = Module::from_file(&engine, "test.wasm")?;

    let mut store = Store::new(&engine, ());

    let instance = Instance::new(&mut store, &module, &[])?;

    let foo = instance.get_typed_func::<i32, i32>(&mut store, "foo")?;

    let result = foo.call(&mut store, 21)?;

    println!("Result = {}", result);

    Ok(())
}