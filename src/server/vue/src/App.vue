<template>
  <div>
    <input type="file" @change="loadImage" />
    <div v-if="imageUrl" class="image-container" :style="imageStyle">
      <svg width="100%" height="100%">
        <polygon :points="polygonPoints" class="polygon" />
      </svg>
      <div
        v-for="(pos, index) in points"
        :key="index"
        class="circle"
        :style="{ top: `${pos.y}px`, left: `${pos.x}px` }"
        @mousedown="startDrag(index, $event)"
      ></div>
    </div>
    <button @click="logpoints">Log points</button>
    <button @click="sendImage">Send image</button>
  </div>
  {{ points }}
  <table>
    <tr v-for="imgUrl in images"><img :src="imgUrl" max-height="20px" /></tr>
  </table>
  
</template>

<script>
import {store} from "./store"

export default {
  data() {
    return {
      store,
      imageUrl: null,
      imageHeight: 0,
      imageWidth: 0,
      imageRatio: 1,
      maxImageWidth: 1024,
      maxImageHeight: 1024,
      images: [],
      points: [
        { x: 0, y: 0 },
        { x: 0, y: 0 },
        { x: 0, y: 0 },
        { x: 0, y: 0 },
      ],
      currentDrag: null,
      dragOptions: {
        draggable: '.circle',
      },
      dragOffset: { x: 0, y: 0 },
    };
  },
  computed: {
    imageStyle() {
      return {
        "background-image": `url(${this.imageUrl})`,
        "background-repeat":"no-repeat",
        width: this.imageWidth + 'px',
        height: this.imageHeight + 'px',
        position: 'relative',
        userSelect: 'none',
      }
    },
    centroid() {
      let xSum = 0;
      let ySum = 0;
      this.points.forEach(point => {
        xSum += point.x;
        ySum += point.y;
      });
      return {x: xSum / this.points.length, y: ySum / this.points.length};
    },
    sortedPoints() {
      const pointsCopy = JSON.parse(JSON.stringify(this.points))
      return pointsCopy.sort((a, b) => {
        const aAngle = Math.atan2(a.y - this.centroid.y, a.x - this.centroid.x);
        const bAngle = Math.atan2(b.y - this.centroid.y, b.x - this.centroid.x);
        return aAngle - bAngle;
      });
    },
    sortedNormalizedPoints() {
      return this.sortedPoints.map( ({x, y}) => { return {
        x: x / this.imageWidth,
        y: y / this.imageHeight
      }} )
    },
    polygonPoints() {
      return this.sortedPoints.map(point => `${point.x},${point.y}`).join(' ');
    }
  },
  methods: {
    loadImage(event) {
      const reader = new FileReader();
      reader.onload = (e) => {
        this.imageUrl = e.target.result;
        
        let img = new Image();
        img.onload = () => {
          this.imageRatio = img.naturalWidth / img.naturalHeight

          this.imageWidth = img.naturalWidth;
          this.imageHeight = img.naturalHeight;
          
          if (this.imageWidth > this.maxImageWidth) {
            this.imageWidth = this.maxImageWidth
            this.imageHeight = parseInt(this.imageWidth / this.imageRatio)
          }
          if (this.imageHeight > this.maxImageHeight) {
            this.imageHeight = this.maxImageHeight
            this.imageWidth = parseInt(this.imageHeight * this.imageRatio)
          }

          this.points = [
            { x: 0, y: 0 },
            { x: this.imageWidth, y: 0 },
            { x: this.imageWidth, y: this.imageHeight },
            { x: 0, y: this.imageHeight },
          ];
        };
        img.src = this.imageUrl;
        console.log(reader)
      };
      reader.readAsDataURL(event.target.files[0]);
    },
    startDrag(index, event) {
      this.currentDrag = index;

      // Calculate the offset
      this.dragOffset.x = event.clientX - this.points[index].x;
      this.dragOffset.y = event.clientY - this.points[index].y;

      // Add mousemove and mouseup listeners to the document
      document.addEventListener('mousemove', this.moveDrag);
      document.addEventListener('mouseup', this.stopDrag);
    },
    moveDrag(event) {
      if (this.currentDrag !== null) {
        this.points[this.currentDrag].x = event.clientX - this.dragOffset.x;
        this.points[this.currentDrag].y = event.clientY - this.dragOffset.y;
      }
    },
    stopDrag() {
      this.currentDrag = null;

      // clamp points
      for (const pos of this.points) {
        if (pos.x < 0) pos.x = 0
        if (pos.x > this.imageWidth) pos.x = this.imageWidth
        if (pos.y < 0) pos.y = 0
        if (pos.y > this.imageHeight) pos.y = this.imageHeight
      }

      // Remove listeners from the document
      document.removeEventListener('mousemove', this.moveDrag);
      document.removeEventListener('mouseup', this.stopDrag);
    },
    logpoints() {
      console.log(this.points);
    },
    sendImage() {
      fetch(this.store.server_host+`/get_transformed_image`, {
        method: "POST",
        more: "no-cors",
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          imageUrl: this.imageUrl,
          points: this.sortedNormalizedPoints 
        })
      }).then(res => res.json()).then(json => {
        this.images = json.images
      })
    }
  },
};
</script>

<style scoped>
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
