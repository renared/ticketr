<template>
  <main>
    <ReceiptUpload v-model="receiptUploadData"/>
    <FormKit type="form" @submit="async () => uploadReceipt()" submit-label="Upload receipt"></FormKit>
    <ReceiptTable ref="receiptTable" :article-images="imageUrls" :article-texts="imageTexts" v-show="imageUrls && imageUrls.length>0"></ReceiptTable>
    <p>Receipt hash: <input type="text" :value="receipt_hash" @input="(e) => e.target.value = receipt_hash"/></p>
    <p>Receipt URL: <input type="text" :value="receiptUrl" @input="(e) => e.target.value = receipt_hash"/></p>
    <FormKit type="radio" v-model="syncMode" label="Sync location" :options="{local:'Local', online:'Online'}" />
    <FormKit type="button" @click="async () => loadReceiptButton()">Load receipt</FormKit>
    <FormKit type="button" @click="async () => saveReceiptButton()">Save receipt</FormKit>
    <FormKit type="button" @click="async () => requestOcr(receipt_hash)">Request OCR</FormKit>

  </main>
</template>

<script>
import {store} from "./store"
import ReceiptUpload from "./components/ReceiptUpload.vue";
import ReceiptTable from "./components/ReceiptTable.vue";
import { FormKit } from "@formkit/vue"
// import * as pako from "pako"

export default {
  components: {
    ReceiptUpload,
    ReceiptTable,
    FormKit
},
  mounted: async function() {
    // Get the 'hash' parameter value from the URL
    const urlParams = new URLSearchParams(window.location.search);
    const encodedHash = urlParams.get('hash');
    if (encodedHash) {
      const hash = decodeURIComponent(encodedHash);
      this.receipt_hash = hash;
      const receiptData = await this.getReceiptOnline(hash);
      console.log(receiptData)
      if (receiptData) this.loadReceipt(receiptData)
    }
  },
  data() {
    return {
      store,
      imageUrls: [],
      imageTexts: [],
      receipt_hash: "",
      syncMode: "local",
      error: null
    }
  },
  computed: {
    receiptUrl() {
      const url = new URL(window.location.origin)
      url.searchParams.append("hash", this.receipt_hash)
      return url.toString()
    }
  },
  methods: {
    uploadReceipt: async function () {
        return fetch(this.store.server_host+`/get_transformed_image`, {
          method: "POST",
          more: "no-cors",
          headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(this.store.receiptUploadData)
        })
        .then(res => res.json())
        .then(json => {
          if (json.status == "exception") this.error = json.exception
          console.log(json)
          this.imageUrls = json.imageUrls
          this.receipt_hash = json.hash
        })
        .catch(reason => this.error = reason)
        .finally(() => {if (this.error) {console.error(this.error);this.error=null}})
      },
    getReceiptData() {
      const receipt_data = {}
      const table = this.$refs.receiptTable
      for (const key of ["form_data", "paidByIdx", "totalPrice", "totals"])
        receipt_data[key] = table.$data[key]
      receipt_data.imageUrls = this.imageUrls
      return receipt_data;
    },
    saveReceipt() {
      window.localStorage.setItem("receipt_data", JSON.stringify(this.getReceiptData()))
    },
    loadReceipt(receipt_data) {
      if (receipt_data === undefined) receipt_data = JSON.parse(window.localStorage.getItem("receipt_data"))
      const table = this.$refs.receiptTable
      this.imageUrls = receipt_data.imageUrls
      setTimeout(() => {
        for (const key of ["form_data", "paidByIdx", "totalPrice", "totals"])
          table.$data[key] = receipt_data[key]
        if (receipt_data.matchedRows !== undefined) this.applyOcrMatchedRows(receipt_data.matchedRows)
        table.formChange()
      }, 0)
      
    },
    updateReceiptOnline: async function () {
      const address = new URL(this.store.server_host+`/update_receipt`)
      address.searchParams.append("hash", this.receipt_hash)
      const receiptData = this.getReceiptData()
      receiptData.imageUrls = undefined // don't upload imageUrls again
      return fetch(address, {
          method: "POST",
          more: "no-cors",
          headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(receiptData)
        })
        .then(res => res.json())
        .then(json => {
          if (json.status == "exception") this.error = json.exception
        })
        .catch(reason => this.error = reason)
        .finally(() => {if (this.error) {console.error(this.error);this.error=null}})
    },
    getReceiptOnline: async function (hash) {
      const address = new URL(this.store.server_host+`/get_receipt`)
      address.searchParams.append("hash", hash)
      return fetch(address, {
          method: "GET",
          more: "no-cors"
        })
        .then(res => res.json())
        .then(receiptData => {
          if (receiptData.status == "exception") throw receiptData.exception
          else return receiptData
        })
        .catch(reason => this.error = reason)
        .finally(() => {if (this.error) {console.error(this.error);this.error=null}})
    },
    loadReceiptButton: async function () {
      if (this.syncMode == "local") this.loadReceipt()
      else {
        return this.getReceiptOnline().then(receiptData => { this.loadReceipt(receiptData) })
      }
    },
    saveReceiptButton: async function () {
      if (this.syncMode == "local") this.saveReceipt()
      else {
        return this.updateReceiptOnline()
      }
    },
    requestOcr: async function (hash) {
      const address = new URL(this.store.server_host+`/request_ocr`)
      address.searchParams.append("hash", hash)
      return fetch(address, {
          method: "GET",
          more: "no-cors"
        })
        .then(res => res.json())
        .then(receiptData => {
          if (receiptData.status == "exception") throw receiptData.exception
          // ocrRows, gptItems, matchedRows
          console.log(receiptData)
          this.applyOcrMatchedRows(receiptData.matchedRows)
        })
        .catch(reason => this.error = reason)
        .finally(() => {if (this.error) {console.error(this.error);this.error=null}})
    },
    applyOcrMatchedRows(matchedRows) {
      this.imageTexts = []
      for (let i = 0 ; i < matchedRows.length ; i++) {
        const row = matchedRows[i]
        if (row) {
          this.imageTexts.push(row[0])
          if (row[1]) setTimeout(() => this.$refs.receiptTable.$data.form_data.articles[i].price = `${row[1]}`, 0)
        } else {
          this.imageTexts.push("")
        }
      }
    }
  },
};
</script>

<style scoped>
main {
  max-width: 1280px;
  margin:auto;
}

.image-container {
  position: relative;
  width: 100%;
  height: 100%;
  background-size: cover;
}

.circle {
  position: absolute;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border:red solid 2px;
  /* background-color: red; */
  cursor: move;
  transform: translate(-12px, -12px)
}

.polygon {
  fill:lime;
  stroke:purple;
  stroke-width:1;
  opacity:0.2;
}
</style>
