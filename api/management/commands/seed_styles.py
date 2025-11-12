from django.core.management.base import BaseCommand
from api.models import Style

DEFAULT_STYLES = [
    dict(
        name="Box Braids", category="braids",
        price_min=140, price_max=220, duration_mins=240,
        image_url="https://cdn2.stylecraze.com/wp-content/uploads/2024/03/Woman-with-long-box-braids-hairstyle.jpg.avif",
        rating_avg=4.8,
    ),
    dict(
        name="Taper Fade", category="cut",
        price_min=35, price_max=55, duration_mins=45,
        image_url="https://menshaircuts.com/wp-content/uploads/2023/04/taper-fade-haircut-classy-mid.jpg",
        rating_avg=4.6,
    ),
    dict(
        name="Twist Out", category="styling",
        price_min=50, price_max=80, duration_mins=60,
        image_url="https://i0.wp.com/therighthairstyles.com/wp-content/uploads/2015/01/1-twist-out-bob-on-shoulder-length-natural-hair.jpg?resize=1080%2C1080&ssl=1",
        rating_avg=4.7,
    ),
    dict(
        name="Balayage Color", category="color",
        price_min=120, price_max=250, duration_mins=150,
        image_url="https://www.southernliving.com/thmb/bhizQMEOnEnn8FB4NRHwv0KV4io=/750x0/filters:no_upscale():max_bytes(150000):strip_icc():format(webp)/23-cbceff443dc14563ab255356a676a225.jpg",
        rating_avg=4.5,
    ),
    dict(
        name="Silk Curls", category="styling",
        price_min=60, price_max=90, duration_mins=75,
        image_url="https://www.fabmood.com/wp-content/uploads/2025/02/7528741.jpg",
        rating_avg=4.4,
    ),
    dict(
        name="Classic Bob", category="cut",
        price_min=50, price_max=70, duration_mins=60,
        image_url="https://theoryhairsalon.com/wp-content/uploads/2024/09/image-3-1.jpg?w=842",
        rating_avg=4.6,
    ),
    dict(
        name="Beard Trim & Line Up", category="cut",
        price_min=14.63, price_max=14.63, duration_mins=30,
        image_url="https://nashfades.ca/cdn/shop/products/image_1000x.jpg?v=1592796785",
        rating_avg=4.8,
    ),
    dict(
        name="Buzz Cut", category="cut",
        price_min=25.00, price_max=35.00, duration_mins=40,
        image_url="https://www.moderngentlemanmagazine.com/wp-content/uploads/2024/06/Classic-Buzz-Cut-Hairstyle-1024x1280.jpg",
        rating_avg=4.9,
    ),
    dict(
        name="Feed-In Cornrows (6 Rows)", category="braids",
        price_min=80.00, price_max=120.00, duration_mins=120,  
        image_url="https://therighthairstyles.com/wp-content/gallery/35926/1/29-alt-Stitch-Braids-and-Tiny-Cornrows-name-justbraidsinfo.jpg",
        rating_avg=4.7,
    ),

]

class Command(BaseCommand):
    help = "Seed default hair styles for development/testing"

    def add_arguments(self, parser):
        parser.add_argument(
            "--fresh", action="store_true",
            help="Delete existing styles before seeding."
        )

    def handle(self, *args, **opts):
        if opts.get("fresh"):
            deleted, _ = Style.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Deleted {deleted} existing Style rows."))

        created, updated = 0, 0
        for s in DEFAULT_STYLES:
            obj, was_created = Style.objects.update_or_create(
                name=s["name"],  # use name as a natural key for idempotency
                defaults={
                    "category": s["category"],
                    "price_min": s["price_min"],
                    "price_max": s["price_max"],
                    "duration_mins": s["duration_mins"],
                    "image_url": s["image_url"],
                    "rating_avg": s.get("rating_avg"),
                },
            )
            created += int(was_created)
            updated += int(not was_created)

        self.stdout.write(self.style.SUCCESS(
            f"Seeding complete. Created: {created}, Updated: {updated}."
        ))

        
        print("Check your styles at: http://localhost:8000/api/styles/")
