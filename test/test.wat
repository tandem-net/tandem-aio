(module
  (func (export "foo") (param i32) (result i32)
    local.get 0
    i32.const 2
    i32.mul
  )
)

;; use command `wat2wasm test/test.wat -o test/test.wasm` to compile this file into wasm