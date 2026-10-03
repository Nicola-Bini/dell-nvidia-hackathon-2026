import type { SurfaceContext } from "./components/types";
import { SurfaceView } from "./SurfaceView";
import { fixtureSurfaces } from "./transport/fixtures";

const inert: SurfaceContext = {
  cartCount: 0,
  ask: () => undefined,
  openView: () => undefined,
  addToCart: () => undefined,
  submit: async () => ({ ok: true }),
};

/** #/gallery: every golden surface, for eyeballing at phone and desktop width. */
export function Gallery() {
  return (
    <div className="cac-gallery">
      {Object.entries(fixtureSurfaces).map(([file, surface]) => (
        <section key={file} className="cac-gallery-item" data-fixture={file}>
          <h2 className="cac-gallery-name">{file}</h2>
          <SurfaceView surface={surface} ctx={inert} />
        </section>
      ))}
    </div>
  );
}
