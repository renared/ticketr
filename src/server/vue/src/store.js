import { reactive } from "vue"

export const store = reactive({

    server_host: window.location.origin.includes(":5173") ? "http://localhost:5000" : window.location.origin,
    receiptUploadData: {},

})