import fitz
from shapely.geometry import Polygon


def bezier(p0, p1, p2, p3, steps=20):
    """三阶Bezier曲线采样"""
    points = []

    for i in range(steps + 1):
        t = i / steps

        x = (
            (1-t)**3 * p0.x +
            3*(1-t)**2*t*p1.x +
            3*(1-t)*t**2*p2.x +
            t**3*p3.x
        )

        y = (
            (1-t)**3 * p0.y +
            3*(1-t)**2*t*p1.y +
            3*(1-t)*t**2*p2.y +
            t**3*p3.y
        )

        points.append((x, y))

    return points


def drawing_area(drawing):

    points = []

    for item in drawing["items"]:

        cmd = item[0]

        # Line
        if cmd == "l":
            p1 = item[1]
            p2 = item[2]

            if not points:
                points.append((p1.x, p1.y))

            points.append((p2.x, p2.y))


        # Bezier curve
        elif cmd == "c":

            p0 = item[1]
            p1 = item[2]
            p2 = item[3]
            p3 = item[4]

            curve_points = bezier(
                p0, p1, p2, p3
            )

            points.extend(curve_points)


    if len(points) < 3:
        return 0


    polygon = Polygon(points)

    return polygon.area



# -------------------------
# main
# -------------------------

doc = fitz.open("bag.pdf")

page = doc[0]

drawings = page.get_drawings()

print("Total drawings:", len(drawings))


drawing0 = drawings[0]

area = drawing_area(drawing0)


print("Drawing[0] area:")
print(area, "pt²")
