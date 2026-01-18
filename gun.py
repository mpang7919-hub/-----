class Gun:
    def __init__(self, gun_type, bullets_num=0):
        self.gun_type = gun_type
        self.bullets_num = bullets_num

    def add_bullets(self, bullets_num):
        self.bullets_num += bullets_num
        print(
            f"Added {bullets_num} bullets. Now {self.bullets_num} bullets in the gun."
        )

    def shoot(self):
        if self.bullets_num > 0:
            self.bullets_num -= 1
            print("Bang!")
            return True
        else:
            print("No bullets")
            return False


if __name__ == "__main__":
    gun = Gun("AK47")
    gun.shoot()
    gun.add_bullets(10)
    gun.shoot()
