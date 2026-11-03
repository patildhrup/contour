import { Plus } from "lucide-react";

export function FAQ() {
  return (
    <section className="faq wrap">
      <div>
        <span className="eyebrow">GOOD TO KNOW</span>
        <h2>
          A little more
          <br />
          clarity.
        </h2>
        <p>Good inputs make great vectors.</p>
      </div>
      <div>
        {[
          [
            "Is this a real vector file?",
            "Yes. Contour creates SVG files containing editable vector paths and fills, never a raster image hidden inside an SVG. Open the result in design tools that support SVG.",
          ],
          [
            "What images work best?",
            "Logos, icons, flat illustrations and line art work best. Photographs, gradients and complex textures create more paths and can lose subtle detail. Small, blurry images cannot recover detail that is missing.",
          ],
          [
            "Does Contour use artificial intelligence?",
            "Contour uses a classical subpixel image-tracing engine with image preprocessing. It is not a trained AI model, generative AI, or a guarantee of perfect reconstruction.",
          ],
          [
            "What happens to my uploads?",
            "Images are sent to the configured conversion server and processed in temporary storage, which is cleaned up after each request. This application does not permanently store uploads or results.",
          ],
          [
            "Can I keep a transparent background?",
            "Yes. Existing transparency is preserved as a binary mask. Semi-transparent edges become transparent or opaque. You can also remove near-white pixels, but this is not automatic subject segmentation.",
          ],
        ].map(([question, answer]) => (
          <details key={question}>
            <summary>
              {question}
              <Plus size={17} />
            </summary>
            <p>{answer}</p>
          </details>
        ))}
      </div>
    </section>
  );
}
