<template>
    <FormKit type="form" v-model="form_data" @submit="() => {}" @change="() => formChange()">
        <table>
            <tr>
                <td></td>
                <td></td>
                <FormKit type="list" name="people" :value="['']" dynamic #default="{ items, node, value }">
                    <td v-for="(item, index) in items">
                        <FormKit
                            :key="item"
                            :index="index"
                            placeholder="Person"
                            prefix-icon="tag"
                            @prefix-icon-click="(e) => paidByIdx = index"
                            suffix-icon="trash"
                            @suffix-icon-click="() => node.input(value.filter((_, i) => i !== index))"
                            />
                        
                    </td>
                    <FormKit type="button" @click="() => node.input(value.concat(''))">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-person-plus-fill" viewBox="0 0 16 16">
                        <path d="M1 14s-1 0-1-1 1-4 6-4 6 3 6 4-1 1-1 1H1zm5-6a3 3 0 1 0 0-6 3 3 0 0 0 0 6z"/>
                        <path fill-rule="evenodd" d="M13.5 5a.5.5 0 0 1 .5.5V7h1.5a.5.5 0 0 1 0 1H14v1.5a.5.5 0 0 1-1 0V8h-1.5a.5.5 0 0 1 0-1H13V5.5a.5.5 0 0 1 .5-.5z"/>
                        </svg>
                    </FormKit>
                </FormKit>
            </tr>
            <FormKit type="list" name="articles">
                <tr v-for="image, i in articleImages" class="articleRow">
                    <FormKit type="group">
                        <td style="text-align:right;" >
                            <img :ref="'image'+i" :src="image" style="max-width: 80%;" /><br />
                            <span v-if="articleTexts[i]" v-html="articleTexts[i]"></span>
                        </td>
                        <td>
                            <FormKit type="number" name="price" value="0.00" step="0.01" suffix-icon="multiCurrency" style="width:8em"/>
                        </td>
                        <FormKit type="list" name="buyers">
                            <td v-for="person, i in form_data.people" style="padding:0px;">
                                <FormKit type="checkbox" :name="'chp'+i" />
                            </td>
                        </FormKit>
                    </FormKit>
                </tr>
            </FormKit>
            <tr v-if="form_data.articles">
                <td>Total</td>
                <td>{{ totalPrice }}</td>
                <td v-for="person, i in form_data.people">{{ totals[i] }}</td>
            </tr>
        </table>
        <br />
        <table v-if="form_data.people?.length>1">
            <tr v-for="person, i in form_data.people">
                <td v-if="i == paidByIdx" style="font-size:1.5em;">{{ (person > 0) ? person : 'Person '+(i+1) }} paid everything.</td>
                <td v-else style="font-size:2em;">{{ (person > 0) ? person : 'Person '+(i+1) }} owes {{ (form_data.people[paidByIdx]>0) ? form_data.people[paidByIdx] : 'Person '+(paidByIdx+1) }} {{ totals[i] }}</td>
            </tr>
        </table>
    </FormKit>
</template>

<script>
import { FormKit } from "@formkit/vue"

export default {
    props: ["articleImages", "articleTexts"],
    components: {
        FormKit
    },
    data() {
        return {
            rows: [],
            form_data: {people:[''], articles:[]},
            form_data_changeCounter: 0,
            totalPrice: 0,
            totals: 0,
            paidByIdx: 0
        }
    },
    watch: {

    },
    computed: {
        priceStyle() {
            return {
            }
        }
    },
    methods: {
        computePrices() {
            const _totals = Array.from({length:this.form_data.people.length}).fill(0)
            let total = 0
            for (const article of this.form_data.articles) {
                total += parseFloat(article.price)
                let buyers_count = 0
                for (const v of article.buyers) {
                    if (v === true) buyers_count += 1
                }
                for (let i = 0 ; i < this.form_data.people.length ; i++) {
                    if (article.buyers[i] === true) _totals[i] += parseFloat(article.price) / buyers_count 
                }
            }
            this.totalPrice = total
            this.totals = _totals
        },
        formChange() {
            setTimeout(() => {
                this.form_data_changeCounter += 1
                this.computePrices()
            }, 0)
        }
    }
}
</script>

<style scoped>
table {
    table-layout:auto;
    width:100%;
}
.articleRow * {
    height:2em
}


</style>