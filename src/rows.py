from PIL import Image
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal.windows import hann
from scipy.signal import sosfiltfilt, butter, find_peaks

def estimate_fundamental_frequency(signal):
    # Calculate FFT
    fft_result = np.fft.rfft(hann(len(signal)) * signal)
    
    # Get the power spectrum
    power_spectrum = np.abs(fft_result)
    #power_spectrum[list(range(len(signal)//64))] = 1e-15
    
    # Find the peak frequency bin
    peak_frequency_bin = np.argmax(power_spectrum)
    
    # If it's not one of the ends (0 or len-1)
    if peak_frequency_bin != 0 and peak_frequency_bin != len(power_spectrum) - 1:
        # Parabolic interpolation
        y0, y1, y2 = np.log(power_spectrum[peak_frequency_bin-1:peak_frequency_bin+2])
        x1 = (y2 - y0) * 0.5 / (2 * y1 - y2 - y0)
        
        # Adjust peak frequency bin
        peak_frequency_bin += x1
    
    # Convert peak frequency bin to frequency
    fundamental_frequency = peak_frequency_bin * 1.0 / len(signal)
    
    return fundamental_frequency

def extract_rows(image):
    if not isinstance(image, np.ndarray):
        image = np.array(image)
    
    scanline = -np.std(image, axis=tuple(range(1,len(image.shape))))
    scanline -= np.mean(scanline)
    freq = estimate_fundamental_frequency(scanline)
    period = 1 / freq
    butter_sos = butter(5, freq*0.9, btype="high", output="sos", fs=1.)
    filtered = sosfiltfilt(butter_sos, scanline)

    peaks, _ = find_peaks(filtered, distance=period*0.75)
    morceaux_de_ticket = []
    for i in range(-1, len(peaks)):
        if i==-1:
            a, b = 0, peaks[0]
        elif i==len(peaks)-1:
            a, b = peaks[-1], len(scanline)
        else:
            a, b = peaks[i], peaks[i+1]
        if (b-a) < 8:
            continue
        morceaux_de_ticket.append(Image.fromarray(image[a:b]).resize((320, int(round((b-a)/image.shape[1]*320))), Image.Resampling.BICUBIC))
    
    return morceaux_de_ticket

if __name__ == "__main__":
    import pytesseract

    img = np.array(Image.open("crop.png"))

    scanline = -np.std(img, axis=tuple(range(1,len(img.shape))))
    scanline -= np.mean(scanline)

    freq_n = estimate_fundamental_frequency(scanline)
    period = 1 / freq_n
    print(period)

    butter_sos = butter(5, freq_n*0.9, btype="high", output="sos", fs=1.)
    filtered = sosfiltfilt(butter_sos, scanline)

    peaks, _ = find_peaks(filtered, distance=period*0.75)

    plt.figure()
    plt.plot(scanline)
    
    plt.figure()
    M = np.abs(np.fft.rfft(hann(len(scanline))*scanline))
    plt.plot(1/np.fft.rfftfreq(len(scanline), 1.)[1:], M[1:])
    plt.xscale("log")
    plt.yscale("log")
    plt.axvline(period)
    
    plt.figure()
    plt.plot(scanline)
    plt.plot(filtered)
    plt.plot(peaks, filtered[peaks], "x")
    plt.show()


    morceaux_de_ticket = []
    for i in range(-1, len(peaks)):
        if i==-1:
            a, b = 0, peaks[0]
        elif i==len(peaks)-1:
            a, b = peaks[-1], len(scanline)
        else:
            a, b = peaks[i], peaks[i+1]
        if (b-a) < 8:
            continue
        morceaux_de_ticket.append(img[a:b])

    # for m in morceaux_de_ticket:
    #     plt.imshow(m)
    #     plt.show()

    from transformers import TrOCRProcessor, VisionEncoderDecoderModel
    processor = TrOCRProcessor.from_pretrained('microsoft/trocr-large-printed')
    model = VisionEncoderDecoderModel.from_pretrained('microsoft/trocr-large-printed').to("cuda:0")

    pixel_values = processor(images=[Image.fromarray(m).resize((256, int(round(m.shape[0]/m.shape[1]*256))), Image.Resampling.LANCZOS).convert("RGB") for m in morceaux_de_ticket], return_tensors="pt").to("cuda:0").pixel_values
    generated_ids = model.generate(pixel_values)
    generated_text = processor.batch_decode(generated_ids, skip_special_tokens=True)

    fig, ax = plt.subplots(len(morceaux_de_ticket), 1)
    for i, m in enumerate(morceaux_de_ticket):
        ax[i].imshow(m)
        print(pytesseract.image_to_string(m))
    plt.show()
    input()