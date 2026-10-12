ALTER TABLE rentals DROP CONSTRAINT rentals_copy_id_fkey;
ALTER TABLE rentals ADD CONSTRAINT rentals_copy_id_fkey FOREIGN KEY(copy_id) REFERENCES rental_copies(id) ON DELETE CASCADE;
